import json
import urllib.request
import http.cookiejar
from getpass import getpass

BASE = "http://127.0.0.1:8000"
cookies = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookies)
)

email = input("Enter your registered email: ")
password = getpass("Enter your password (hidden): ")

payload = json.dumps({
    "email": email,
    "password": password
}).encode("utf-8")

request = urllib.request.Request(
    BASE + "/login",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Origin": "http://localhost:5173"
    },
    method="POST"
)

try:
    with opener.open(request, timeout=15) as response:
        print("Login HTTP status:", response.status)
        print("Session cookie received:", any(
            cookie.name == "smart_session" for cookie in cookies
        ))

    request = urllib.request.Request(BASE + "/me")
    with opener.open(request, timeout=15) as response:
        print("Session validation HTTP status:", response.status)
        print("Authenticated user:", response.read().decode("utf-8"))

except Exception as error:
    print("Authentication test failed:", error)
