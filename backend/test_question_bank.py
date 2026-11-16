from __future__ import annotations

import getpass
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
QUESTIONS_DIR = BACKEND_DIR / "questions"
API_BASE_URL = os.getenv("SMART_API_URL", "http://localhost:8000").rstrip("/")
RUN_URL = f"{API_BASE_URL}/run"
LOGIN_URL = f"{API_BASE_URL}/login"
ORIGIN = "http://localhost:5173"
LANGUAGES = ("Python", "C", "C++", "Java")

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

    with OPENER.open(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    if not QUESTIONS_DIR.is_dir():
        print(f"ERROR: Questions folder not found: {QUESTIONS_DIR}")
        return 2

    files = sorted(QUESTIONS_DIR.glob("*.json"))
    if not files:
        print(f"ERROR: No question JSON files found in {QUESTIONS_DIR}")
        return 2

    print(f"API: {RUN_URL}")
    if not authenticate():
        print("ERROR: Authentication failed or session cookie missing.")
        return 2

    print(f"Questions found: {len(files)}")
    print("Testing each question's first example in Python, C, C++, and Java...\n")

    passed = 0
    failed = 0
    started = time.time()

    for path in files:
        try:
            question = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            failed += len(LANGUAGES)
            print(f"[FAIL] {path.name}: invalid JSON: {exc}")
            continue

        question_id = question.get("id", path.stem)
        examples = question.get("examples") or []

        if not examples:
            failed += len(LANGUAGES)
            print(f"[FAIL] {question_id}: no example input/output available")
            continue

        example = examples[0]
        input_data = str(example.get("input", ""))
        expected = normalize(example.get("output", ""))
        starter_code = question.get("starter_code") or {}

        for language in LANGUAGES:
            code = starter_code.get(language)
            label = f"{question_id:<25} {language:<6}"

            if not code:
                failed += 1
                print(f"[FAIL] {label} starter code missing")
                continue

            try:
                result = post_run(question_id, language, code, input_data)

                if result.get("status") != "success":
                    failed += 1
                    detail = result.get("error") or result.get("output") or result
                    print(f"[FAIL] {label} execution error: {str(detail).strip()[:240]}")
                    continue

                actual = normalize(result.get("output", ""))

                if actual == expected:
                    passed += 1
                    print(f"[PASS] {label} output: {actual}")
                else:
                    failed += 1
                    print(f"[FAIL] {label} expected: {expected!r} | got: {actual!r}")

            except urllib.error.HTTPError as exc:
                failed += 1
                detail = exc.read().decode("utf-8", errors="replace")
                print(f"[FAIL] {label} HTTP {exc.code}: {detail[:240]}")

            except Exception as exc:
                failed += 1
                print(f"[FAIL] {label} request failed: {exc}")

    total = passed + failed
    print("\n" + "=" * 62)
    print(f"RESULT: {passed}/{total} checks passed; {failed} failed.")
    print(f"Elapsed: {time.time() - started:.1f} seconds")

    if failed:
        print("Review the FAIL lines above.")
        return 1

    print("All starter programs produced the expected output for their first example.")
    print("Note: this is a smoke test, not the full hidden test suite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
