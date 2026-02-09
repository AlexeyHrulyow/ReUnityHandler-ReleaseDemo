# debug_api.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from reunity_app.main import app

client = TestClient(app)

print("🔍 Проверка доступных эндпоинтов:")
for route in app.routes:
    if hasattr(route, "path"):
        methods = route.methods if hasattr(route, "methods") else ["GET"]
        print(f"  {','.join(methods)} {route.path}")

print("\n📋 Проверка эндпоинтов:")
endpoints = [
    ("GET", "/"),
    ("GET", "/health"),
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/tables"),
    ("GET", "/api/v1/info"),
    ("GET", "/api/v1/cases"),
    ("GET", "/api/v1/documents"),
]

for method, path in endpoints:
    try:
        if method == "GET":
            response = client.get(path)
        elif method == "POST":
            response = client.post(path)

        print(f"{method} {path}: {response.status_code}")
    except Exception as e:
        print(f"{method} {path}: ERROR - {e}")