import json
import urllib.request
import urllib.error
import http.cookiejar
from getpass import getpass

BASE = "http://127.0.0.1:8000"

def make_opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar)
    )

email = input("Registered email: ").strip()
password = getpass("Password (hidden): ")

# Login and retain the session cookie
opener = make_opener()
login_data = json.dumps({
    "email": email,
    "password": password
}).encode()

login_request = urllib.request.Request(
    BASE + "/login",
    data=login_data,
    headers={
        "Content-Type": "application/json",
        "Origin": "http://localhost:5173"
    },
    method="POST"
)

try:
    with opener.open(login_request, timeout=20) as response:
        print("Login:", response.status)

    payload = json.dumps({
        "language": "python",
        "code": "print('Day 5 security test passed')",
        "question_id": "day5-security-test",
        "input_data": ""
    }).encode()

    run_request = urllib.request.Request(
        BASE + "/run",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Origin": "http://localhost:5173"
        },
        method="POST"
    )

    with opener.open(run_request, timeout=60) as response:
        print("Authenticated /run status:", response.status)
        print("Execution result:", response.read().decode())

except Exception as error:
    print("Authenticated test failed:", error)

# Test /run without a session cookie
anonymous_opener = make_opener()
anonymous_request = urllib.request.Request(
    BASE + "/run",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Origin": "http://localhost:5173"
    },
    method="POST"
)

try:
    with anonymous_opener.open(anonymous_request, timeout=20) as response:
        print("Unauthenticated /run status:", response.status)
except urllib.error.HTTPError as error:
    print("Unauthenticated /run status:", error.code)
    print("Unauthenticated response:", error.read().decode())
