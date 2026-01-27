import requests

base = "http://192.168.0.84:8000"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImM1NTlkOWM1LTk2OWQtNDk1MC05YTVhLWY3MGJlMTY1YTk1ZiIsImV4cCI6MTc3MTU3NTMzMywianRpIjoiMjgyYThkYWYtNzc4NS00MjliLWI1Y2ItMWIxYzFlNmMyZTE0MyJ9.VFDZueb-nRuU3ISLw4eDM6wKdOgGmaS1TjgExnErIY4"

headers = {
    "Authorization": token,
    "Content-Type": "application/json"
}

# 가능한 경로들 테스트
paths = [
    "/load",
    "/ping",
]

for path in paths:
    try:
        r = requests.get(f"{base}{path}", headers=headers, timeout=2)
        print(f"{path}: {r.status_code}")
    except Exception as e:
        print(f"{path}: Error - {str(e)[:50]}")
