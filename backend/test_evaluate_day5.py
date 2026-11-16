import json
import urllib.request
import urllib.error
import http.cookiejar
from getpass import getpass

BASE = "http://127.0.0.1:8000"

email = input("Registered email: ").strip()
password = getpass("Password (hidden): ")

cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookies)
)

def post(path, payload):
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Origin": "http://localhost:5173"
        },
        method="POST"
    )
    return opener.open(request, timeout=90)

try:
    with post("/login", {
        "email": email,
        "password": password
    }) as response:
        print("Login status:", response.status)

    code = '''text = input()
vowels = "aeiou"
count = 0
for char in text.lower():
    if char in vowels:
        count += 1
print(count)'''

    payload = {
        "language": "Python",
        "question_id": "count_vowels",
        "code": code,
        "input_data": ""
    }

    with post("/evaluate", payload) as response:
        result = json.loads(response.read().decode("utf-8"))
        print("Authenticated /evaluate status:", response.status)
        print("Evaluation result:")
        print(json.dumps(result, indent=2))

except urllib.error.HTTPError as error:
    print("HTTP error:", error.code)
    print(error.read().decode("utf-8"))
except Exception as error:
    print("Test failed:", str(error))

# Check unauthenticated access
anonymous = urllib.request.build_opener()

request = urllib.request.Request(
    BASE + "/evaluate",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Origin": "http://localhost:5173"
    },
    method="POST"
)

try:
    with anonymous.open(request, timeout=30) as response:
        print("Unauthenticated /evaluate status:", response.status)
except urllib.error.HTTPError as error:
    print("Unauthenticated /evaluate status:", error.code)
    print("Response:", error.read().decode("utf-8"))
