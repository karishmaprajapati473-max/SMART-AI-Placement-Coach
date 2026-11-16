import logging
from logging.handlers import RotatingFileHandler
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, Response, HTTPException
from pydantic import BaseModel, Field, EmailStr
import subprocess
import json
import tempfile
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from weak_concept import diagnose_submission
from auth import get_connection
from auth import (
    init_db,
    create_user,
    verify_user,
    create_session,
    get_user_by_session,
    revoke_session,
    save_coding_attempt,
)

from ml.data_collection import (
    ensure_ml_collection_tables,
    get_ml_consent,
    set_ml_consent,
    store_error_candidate,
    list_pending_samples,
    review_sample,
    reject_sample,
    export_approved_samples,
)

# Logging configuration
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("smart_ai")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = RotatingFileHandler(
        LOG_DIR / "backend.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

app = FastAPI(
    title="Smart AI Placement Coach",
    description="Backend API for coding practice and evaluation",
    version="0.1.0",
)

limiter = Limiter(key_func=get_remote_address)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)

TRUSTED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
}

@app.middleware("http")
async def csrf_origin_check(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")

        if not origin or origin not in TRUSTED_ORIGINS:
            return JSONResponse(
                status_code=403,
                content={"detail": "Request origin not allowed."},
            )

    return await call_next(request)

class CodeSubmission(BaseModel):
    language: str = Field(min_length=1, max_length=30)
    code: str = Field(min_length=1, max_length=10000)
    
    question_id: str = Field(min_length=1, max_length=100)

    input_data: str = Field(default="", max_length=10000)
    revised_concept: str | None = Field(default=None, max_length=100)

class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MLConsentRequest(BaseModel):
    enabled: bool

class MLReviewRequest(BaseModel):
    action: str = Field(min_length=1, max_length=10)
    label: str | None = Field(default=None, max_length=100)
    reviewer_note: str = Field(default="", max_length=1000)

class RevisionEventRequest(BaseModel):
    weak_concept: str = Field(min_length=1, max_length=100)
    question_id: str = Field(min_length=1, max_length=100)
    topic: str = Field(default="", max_length=100)
    language: str = Field(default="Python", max_length=30)
    event_key: str = Field(min_length=1, max_length=100)




def require_reviewer(request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Please login first."
        )

    if user.get("role") != "reviewer":
        raise HTTPException(
            status_code=403,
            detail="Reviewer access required."
        )

    return user

def run_python_code(code: str, input_data: str = ""):
    with tempfile.TemporaryDirectory() as temp_dir:
        code_path = os.path.join(temp_dir, "main.py")

        with open(code_path, "w", encoding="utf-8") as file:
            file.write(code)

        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm", "-i",
                    "--network", "none",
                    "--memory", "128m",
                    "--cpus", "0.5",
                    "--pids-limit", "64",
                    "--read-only",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                    "--user", "65534:65534",
                    "--cap-drop", "ALL",
                    "--security-opt", "no-new-privileges",
                    "--mount",
                    f"type=bind,source={code_path},target=/app/main.py,readonly",
                    "--workdir", "/app",
                    "python:3.12-slim",
                    "python", "-I", "/app/main.py",
                ],
                capture_output=True,
                text=True,
                input=input_data,
                timeout=20,
                check=False,
            )

            return {
                "output": result.stdout[:5000],
                "error": result.stderr[:5000],
                "exit_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "output": "",
                "error": "Execution timed out (5 seconds limit).",
                "exit_code": None,
            }

        except OSError:
            return {
                "output": "",
                "error": "Could not start Docker. Check that Docker Desktop is running.",
                "exit_code": None,
            }

def run_code_in_docker(language: str, code: str, input_data: str = ""):
    language = language.strip().lower()

    if language in ["python", "python3"]:
        filename = "main.py"
        image = "python:3.12-slim"
        command = ["python", "-I", "/app/main.py"]

    elif language == "c":
        filename = "main.c"
        image = "gcc:14"
        command = [
            "sh", "-c",
            "gcc -O2 -o /tmp/program /app/main.c && /tmp/program"
        ]

    elif language in ["c++", "cpp"]:
        filename = "main.cpp"
        image = "gcc:14"
        command = [
            "sh", "-c",
            "g++ -O2 -o /tmp/program /app/main.cpp && /tmp/program"
        ]

    elif language == "java":
        filename = "Main.java"
        image = "eclipse-temurin:21"
        command = [
            "sh", "-c",
            "javac -d /tmp /app/Main.java && java -cp /tmp Main"
        ]

    else:
        return {
            "output": "",
            "error": "Unsupported language.",
            "exit_code": 1,
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        code_path = os.path.join(temp_dir, filename)

        with open(code_path, "w", encoding="utf-8") as file:
            file.write(code)

        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm", "-i",
                    "--network", "none",
                    "--memory", "256m",
                    "--cpus", "0.5",
                    "--pids-limit", "64",
                    "--read-only",
                    "--tmpfs", "/tmp:rw,exec,nosuid,size=64m",
                    "--user", "65534:65534",
                    "--cap-drop", "ALL",
                    "--security-opt", "no-new-privileges",
                    "--mount",
                    f"type=bind,source={code_path},target=/app/{filename},readonly",
                    "--workdir", "/app",
                    image,
                    *command,
                ],
                capture_output=True,
                text=True,
                input=input_data,
                timeout=20,
                check=False,
            )

            return {
                "output": result.stdout[:5000],
                "error": result.stderr[:5000],
                "exit_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "output": "",
                "error": "Execution timed out (20 seconds limit).",
                "exit_code": None,
            }

        except OSError:
            return {
                "output": "",
                "error": "Could not start Docker. Check that Docker Desktop is running.",
                "exit_code": None,
            }


def normalize_output(output: str) -> str:
    return output.strip()


def evaluate_test_cases(question: dict, code: str, language: str = "python"):
    results = []
    diagnostic_messages = []
    passed = 0

    for index, test_case in enumerate(question["test_cases"], start=1):
        run_result = run_code_in_docker(
            language,
            code,
            test_case["input"],
        )

        actual_output = normalize_output(run_result["output"])
        expected_output = normalize_output(
            test_case["expected_output"]
        )

        is_passed = (
            run_result["exit_code"] == 0
            and actual_output == expected_output
        )

        if is_passed:
            passed += 1
        else:
            error_message = run_result.get("error", "")
            if error_message:
                diagnostic_messages.append(error_message)

        results.append({
            "test_case": index,
            "passed": is_passed
        })

    return {
        "passed": passed,
        "total": len(question["test_cases"]),
        "results": results,
        "diagnostic_messages": diagnostic_messages
    }


@app.get("/")
def home():
    return {
        "message": "Smart AI Placement Coach backend is running!"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }



@app.post("/run")
def run_code(submission: CodeSubmission, request: Request):
    # Verify the logged-in user
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please login again."
        )

    # Execute code inside the restricted Docker container
    result = run_code_in_docker(
        submission.language,
        submission.code,
        submission.input_data,
    )

    if result["exit_code"] != 0:
        return {
            "status": "error",
            "output": result["output"],
            "error": result["error"],
        }

    return {
        "status": "success",
        "output": result["output"],
        "error": "",
    }




@app.post("/evaluate")
def evaluate_code(submission: CodeSubmission, request: Request):

    # Verify the logged-in student
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please login again."
        )

    # Load the selected question
    question_path = QUESTIONS_DIR / f"{submission.question_id}.json"

    if not question_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Question not found."
        )

    with open(question_path, "r", encoding="utf-8") as file:
        question = json.load(file)

    # Evaluate submitted code
    result = evaluate_test_cases(
        question,
        submission.code,
        submission.language,
    )

    # Run ML-based concept diagnosis
    diagnosis = diagnose_submission(
        question=question,
        evaluation=result,
        diagnostic_messages=result.get("diagnostic_messages", []),
        language=submission.language,
        code_snippet=submission.code,
    )

    # Optional ML research collection: only opted-in users are eligible.
    # Samples are sanitized and remain pending human review (no auto-labeling).
    try:
        store_error_candidate(
            user_id=user["id"],
            question_id=submission.question_id,
            language=submission.language,
            topic=question.get("topic", "Unknown"),
            diagnostic_messages=result.get("diagnostic_messages", []),
            code_snippet=submission.code,
            passed=result["passed"],
            total=result["total"],
            personal_values=(user.get("name", ""), user.get("email", "")),
        )
    except Exception as collection_error:
        # Research collection must never break a student's evaluation.
        print(
            f"[ML COLLECTION] Sample collection skipped: {type(collection_error).__name__}",
            flush=True,
        )

    # Save the attempt under the authenticated student
    attempt_id = save_coding_attempt(
        user_id=user["id"],
        question_id=submission.question_id,
        topic=question.get("topic", "Unknown"),
        language=submission.language,
        passed=result["passed"],
        total=result["total"],
        diagnosis=diagnosis,
        revised_concept=submission.revised_concept,
    )

    return {
        "question_id": submission.question_id,
        "status": (
            "success"
            if result["passed"] == result["total"]
            else "failed"
        ),
        "passed": result["passed"],
        "total": result["total"],
        "results": result["results"],
        "diagnosis": diagnosis,
        "attempt_id": attempt_id,
    }


QUESTIONS_DIR = Path(__file__).parent / "questions"


@app.get("/questions/{question_id}")
def get_question(question_id: str):
    question_path = QUESTIONS_DIR / f"{question_id}.json"

    if not question_path.is_file():
        return {
            "status": "error",
            "message": "Question not found"
        }

    with open(question_path, "r", encoding="utf-8") as file:
        question = json.load(file)

    # Hidden test cases student ko return nahi karne
    question.pop("test_cases", None)

    return question


@app.on_event("startup")
def startup_event():
    init_db()
    ensure_ml_collection_tables()


@app.get("/ml/consent")
def read_ml_consent(request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")
    return {"status": "success", **get_ml_consent(user["id"])}

@app.get("/ml/review/pending")
def get_pending_ml_samples(request: Request):
    require_reviewer(request)

    return {
        "status": "success",
        "samples": list_pending_samples()
    }


@app.post("/ml/review/{sample_id}")
def review_ml_sample(
    sample_id: int,
    payload: MLReviewRequest,
    request: Request
):
    require_reviewer(request)

    if payload.action == "approve":
        if not payload.label:
            raise HTTPException(
                status_code=422,
                detail="A valid human-reviewed label is required."
            )

        try:
            review_sample(
                sample_id=sample_id,
                label=payload.label,
                reviewer_note=payload.reviewer_note
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))

    elif payload.action == "reject":
        try:
            reject_sample(
                sample_id=sample_id,
                reviewer_note=payload.reviewer_note
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))

    else:
        raise HTTPException(
            status_code=422,
            detail="Action must be approve or reject."
        )

    return {
        "status": "success",
        "sample_id": sample_id,
        "action": payload.action
    }


@app.get("/ml/review/export")
def export_ml_training_data(request: Request):
    require_reviewer(request)

    samples = export_approved_samples()

    return {
        "status": "success",
        "count": len(samples),
        "samples": samples
    }

@app.put("/ml/consent")
def update_ml_consent(payload: MLConsentRequest, request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")
    result = set_ml_consent(user["id"], payload.enabled)
    return {"status": "success", **result}


@app.post("/signup")
@limiter.limit("5/minute")
def signup(request: Request, payload: SignupRequest):
    try:
        user = create_user(
            payload.name,
            payload.email,
            payload.password,
        )
        return {
            "status": "success",
            "message": "Account created successfully.",
            "user": user,
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, payload: LoginRequest, response: Response):
    user = verify_user(payload.email, payload.password)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    token = create_session(user["id"])

    response.set_cookie(
        key="smart_session",
        value=token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=86400,
        path="/",
    )

    return {
        "status": "success",
        "message": "Login successful.",
        "user": user,
    }

@app.get("/me")
def get_current_user(request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please login again."
        )

    return {
        "status": "success",
        "user": user
    }


@app.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("smart_session")

    if token:
        revoke_session(token)

    response.delete_cookie(
        key="smart_session",
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/"
    )

    return {
        "status": "success",
        "message": "Logged out successfully."
    }


@app.post("/progress/revision-event")
def record_revision_event(payload: RevisionEventRequest, request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Please login first."
        )

    allowed_concepts = {
        "Syntax & Indentation",
        "Variables & Naming",
        "Data Types & Input Handling",
        "Arrays & Indexing",
        "Loops & Iteration",
        "Recursion",
        "Function Usage",
        "Algorithm Efficiency",
    }

    if payload.weak_concept not in allowed_concepts:
        raise HTTPException(
            status_code=422,
            detail="Invalid weak concept."
        )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO revision_events (
                user_id, weak_concept, question_id,
                topic, language, event_key
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, event_key) DO NOTHING
            """,
            (
                user["id"],
                payload.weak_concept,
                payload.question_id,
                payload.topic.strip(),
                payload.language.strip(),
                payload.event_key,
            )
        )

        saved_event = connection.execute(
            """
            SELECT id FROM revision_events
            WHERE user_id = ? AND event_key = ?
            """,
            (user["id"], payload.event_key)
        ).fetchone()

    created = cursor.rowcount == 1

    return {
        "status": "success",
        "created": created,
        "message": (
            "Revision event recorded."
            if created else "Revision event already recorded."
        ),
        "event_id": saved_event["id"] if saved_event else None
    }



@app.get("/progress/revision-improvement")
def get_revision_improvement(request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Please login first."
        )

    query = """
    WITH post_candidates AS (
        SELECT
            a.*,
            (
                SELECT e.id
                FROM revision_events e
                WHERE e.user_id = a.user_id
                  AND e.question_id = a.question_id
                  AND REPLACE(LOWER(e.weak_concept), ' ', '') =
                      REPLACE(LOWER(a.revised_concept), ' ', '')
                  AND datetime(e.created_at) <= datetime(a.created_at)
                ORDER BY datetime(e.created_at) DESC, e.id DESC
                LIMIT 1
            ) AS revision_id
        FROM coding_attempts a
        WHERE a.user_id = ?
          AND a.revised_concept IS NOT NULL
    ),
    ranked AS (
        SELECT
            pc.*,
            e.created_at AS revision_time,
            ROW_NUMBER() OVER (
                PARTITION BY pc.revision_id
                ORDER BY datetime(pc.created_at), pc.id
            ) AS post_rank
        FROM post_candidates pc
        JOIN revision_events e ON e.id = pc.revision_id
        WHERE pc.revision_id IS NOT NULL
    ),
    paired_ids AS (
        SELECT
            r.*,
            (
                SELECT b.id
                FROM coding_attempts b
                WHERE b.user_id = r.user_id
                  AND b.question_id = r.question_id
                  AND REPLACE(LOWER(COALESCE(b.weak_concept, '')), ' ', '') =
                      REPLACE(LOWER(r.revised_concept), ' ', '')
                  AND datetime(b.created_at) < datetime(r.revision_time)
                ORDER BY datetime(b.created_at) DESC, b.id DESC
                LIMIT 1
            ) AS before_attempt_id
        FROM ranked r
        WHERE r.post_rank = 1
    )
    SELECT
        p.question_id,
        p.revised_concept AS weak_concept,
        p.revision_time,
        b.passed AS before_passed,
        b.total AS before_total,
        p.passed AS after_passed,
        p.total AS after_total
    FROM paired_ids p
    JOIN coding_attempts b ON b.id = p.before_attempt_id
    WHERE b.total > 0 AND p.total > 0
    ORDER BY datetime(p.revision_time) DESC
    LIMIT 50
    """

    with get_connection() as connection:
        rows = connection.execute(query, (user["id"],)).fetchall()

    pairs = []

    for row in rows:
        item = dict(row)
        before_rate = round(item["before_passed"] / item["before_total"] * 100, 1)
        after_rate = round(item["after_passed"] / item["after_total"] * 100, 1)

        pairs.append({
            "question_id": item["question_id"],
            "weak_concept": item["weak_concept"],
            "revision_time": item["revision_time"],
            "before_passed": item["before_passed"],
            "before_total": item["before_total"],
            "before_rate": before_rate,
            "after_passed": item["after_passed"],
            "after_total": item["after_total"],
            "after_rate": after_rate,
            "change_percentage_points": round(after_rate - before_rate, 1),
        })

    return {
        "status": "success",
        "matched_count": len(pairs),
        "pairs": pairs,
    }


@app.get("/progress/me")
def get_my_progress(request: Request):
    token = request.cookies.get("smart_session")
    user = get_user_by_session(token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Please login again."
        )

    user_id = user["id"]

    with get_connection() as connection:

        summary = connection.execute("""
            SELECT
                COUNT(*) AS total_attempts,
                SUM(CASE
                    WHEN total > 0 AND passed = total THEN 1
                    ELSE 0
                END) AS successful_attempts,
                COUNT(DISTINCT CASE
                    WHEN total > 0 AND passed = total
                    THEN question_id
                END) AS unique_questions_solved,
                ROUND(
                    AVG(
                        CASE WHEN total > 0
                        THEN 1.0 * passed / total
                        ELSE 0 END
                    ) * 100, 1
                ) AS average_test_pass_rate
            FROM coding_attempts
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        topics = connection.execute("""
            SELECT
                topic,
                COUNT(*) AS attempts,
                SUM(CASE
                    WHEN total > 0 AND passed = total THEN 1
                    ELSE 0
                END) AS successful_attempts
            FROM coding_attempts
            WHERE user_id = ?
            GROUP BY topic
            ORDER BY attempts DESC
        """, (user_id,)).fetchall()

        weaknesses = connection.execute("""
            SELECT
                weak_concept,
                COUNT(*) AS occurrences
            FROM coding_attempts
            WHERE user_id = ?
              AND weak_concept IS NOT NULL
            GROUP BY weak_concept
            ORDER BY occurrences DESC
        """, (user_id,)).fetchall()

        recent = connection.execute("""
            SELECT
                question_id,
                topic,
                language,
                passed,
                total,
                weak_concept,
                diagnosis_method,
                created_at
            FROM coding_attempts
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 5
        """, (user_id,)).fetchall()

        
        daily_activity = connection.execute("""
            SELECT
                DATE(created_at) AS activity_date,
                COUNT(*) AS attempts,
                SUM(
                    CASE
                        WHEN total > 0 AND passed = total THEN 1
                        ELSE 0
                    END
                ) AS successful_attempts,
                ROUND(
                    AVG(
                        CASE
                            WHEN total > 0
                            THEN 100.0 * passed / total
                            ELSE 0
                        END
                    ), 1
                ) AS avg_test_pass_rate
            FROM coding_attempts
            WHERE user_id = ?
              AND created_at >= datetime('now', '-6 days')
            GROUP BY DATE(created_at)
            ORDER BY activity_date ASC
        """, (user_id,)).fetchall()


    return {
        "status": "success",
        "summary": dict(summary),
        "topics": [dict(row) for row in topics],
        "recent_attempts": [dict(row) for row in recent],
        "daily_activity": [dict(row) for row in daily_activity],
        "weak_concepts": [dict(row) for row in weaknesses]
    }
