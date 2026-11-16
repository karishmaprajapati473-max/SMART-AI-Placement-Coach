from __future__ import annotations

import concurrent.futures
import getpass
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from threading import Lock

BACKEND_DIR = Path(__file__).resolve().parent
QUESTIONS_DIR = BACKEND_DIR / "questions"
API_BASE_URL = os.getenv("SMART_API_URL", "http://localhost:8000").rstrip("/")
RUN_URL = f"{API_BASE_URL}/run"
LOGIN_URL = f"{API_BASE_URL}/login"
ORIGIN = "http://localhost:5173"
LANGUAGES = ("Python", "C", "C++", "Java")
MAX_WORKERS = max(1, min(3, int(os.getenv("SMART_TEST_WORKERS", "2"))))
REQUEST_TIMEOUT_SECONDS = 180

_print_lock = Lock()
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(COOKIE_JAR)
)


def normalize(value: object) -> str:
    return " ".join(str(value if value is not None else "").split())


def authenticate() -> bool:
    email = input("Registered email: ").strip()
    password = getpass.getpass("Password (hidden): ")

    payload = json.dumps({
        "email": email,
        "password": password,
    }).encode("utf-8")

    request = urllib.request.Request(
        LOGIN_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Origin": ORIGIN,
        },
        method="POST",
    )

    try:
        with OPENER.open(request, timeout=20) as response:
            print("Login status:", response.status)

        authenticated = any(
            cookie.name == "smart_session"
            for cookie in COOKIE_JAR
        )
        print("Session cookie received:", authenticated)
        return authenticated

    except Exception as exc:
        print("Login failed:", exc)
        return False


def post_run(question_id: str, language: str, code: str, input_data: str) -> dict:
    payload = {
        "language": language,
        "question_id": question_id,
        "code": code,
        "input_data": input_data,
    }

    request = urllib.request.Request(
        RUN_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Origin": ORIGIN,
        },
        method="POST",
    )

    with OPENER.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def run_one(task: tuple[str, str, str, int, str, str]) -> tuple[bool, str, str]:
    question_id, language, code, case_number, input_data, expected = task
    label = f"{question_id:<25} {language:<6} case {case_number}"

    try:
        result = post_run(question_id, language, code, input_data)

        if result.get("status") != "success":
            detail = result.get("error") or result.get("output") or result
            return False, label, f"execution error: {str(detail).strip()[:220]}"

        actual = normalize(result.get("output", ""))

        if actual == expected:
            return True, label, f"output: {actual}"

        return False, label, f"expected: {expected!r} | got: {actual!r}"

    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, label, f"HTTP {exc.code}: {detail[:220]}"

    except Exception as exc:
        return False, label, f"request failed: {exc}"


def main() -> int:
    if not QUESTIONS_DIR.is_dir():
        print(f"ERROR: Questions folder not found: {QUESTIONS_DIR}")
        return 2

    files = sorted(QUESTIONS_DIR.glob("*.json"))

    if not files:
        print(f"ERROR: No question JSON files found in {QUESTIONS_DIR}")
        return 2

    if not authenticate():
        print("ERROR: Authentication failed or session cookie missing.")
        return 2

    tasks: list[tuple[str, str, str, int, str, str]] = []
    question_count = 0

    for path in files:
        try:
            question = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"ERROR: Invalid JSON in {path.name}: {exc}")
            return 2

        question_id = str(question.get("id", path.stem))
        starter_code = question.get("starter_code") or {}
        test_cases = question.get("test_cases") or []

        if not test_cases:
            print(f"ERROR: {question_id} has no test_cases")
            return 2

        question_count += 1

        for language in LANGUAGES:
            code = starter_code.get(language)

            if not code:
                print(f"ERROR: {question_id} is missing {language} starter code")
                return 2

            for index, case in enumerate(test_cases, start=1):
                tasks.append((
                    question_id,
                    language,
                    code,
                    index,
                    str(case.get("input", "")),
                    normalize(case.get("expected_output", "")),
                ))

    print(f"API: {RUN_URL}")
    print(f"Questions: {question_count}")
    print(f"Languages: {', '.join(LANGUAGES)}")
    print(f"Total checks: {len(tasks)} | Concurrent workers: {MAX_WORKERS}")
    print("Running all starter programs against all JSON test cases...\n", flush=True)

    started = time.time()
    passed = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as pool:
        futures = [pool.submit(run_one, task) for task in tasks]

        for future in concurrent.futures.as_completed(futures):
            ok, label, detail = future.result()

            with _print_lock:
                print(f"[{'PASS' if ok else 'FAIL'}] {label} {detail}", flush=True)

            if ok:
                passed += 1
            else:
                failed += 1
                failures.append((label, detail))

    elapsed = time.time() - started

    print("\n" + "=" * 68)
    print(f"RESULT: {passed}/{len(tasks)} checks passed; {failed} failed.")
    print(f"Elapsed: {elapsed:.1f} seconds")

    if failures:
        print("\nFailures:")
        for label, detail in failures:
            print(f" - {label}: {detail}")
        return 1

    print("All starter programs passed every JSON test case for all four languages.")
    print("Note: this validates starter-code execution via /run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
