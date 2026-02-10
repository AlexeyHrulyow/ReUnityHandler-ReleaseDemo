# test_api_direct.py
import requests
import json

# Тестируем без авторизации сначала
print("1. Тест без авторизации:")
response = requests.get("http://localhost:8000/api/v1/documents?case_id=4")
print(f"   Статус: {response.status_code}")
print(f"   Ответ: {response.text[:200]}")

# Теперь с авторизацией
print("\n2. Тест с авторизацией:")
# Сначала получим токен
login_data = {
    "username": "admin",  # Используйте реальные данные
    "password": "admin123"
}

try:
    # Попробуем получить токен
    auth_response = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        data=login_data
    )

    if auth_response.status_code == 200:
        token = auth_response.json()["access_token"]
        print(f"   Токен получен")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Тест документов
        response = requests.get(
            "http://localhost:8000/api/v1/documents?case_id=4",
            headers=headers
        )
        print(f"   Статус документов: {response.status_code}")
        print(f"   Ответ: {response.text[:500]}")

        # Тест других эндпоинтов
        print("\n3. Тест других эндпоинтов:")
        for endpoint in ["/health", "/api/v1/health", "/api/v1/tables", "/api/v1/cases"]:
            response = requests.get(f"http://localhost:8000{endpoint}", headers=headers)
            print(f"   {endpoint}: {response.status_code}")

    else:
        print(f"   Ошибка авторизации: {auth_response.status_code}")
        print(f"   Ответ: {auth_response.text}")

except Exception as e:
    print(f"   Ошибка: {e}")