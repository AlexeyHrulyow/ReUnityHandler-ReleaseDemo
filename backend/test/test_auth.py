#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"


def test_login():
    """Тест аутентификации"""
    print("1. Тестируем вход...")

    # Пробуем войти с данными администратора
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )

    print(f"   Статус: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"   Успех! Токен получен")
        print(f"   Тип токена: {data.get('token_type')}")
        print(f"   Длина токена: {len(data.get('access_token', ''))}")
        return data.get('access_token')
    else:
        print(f"   Ошибка: {response.text}")
        return None


def test_me_endpoint(token):
    """Тест endpoint /me"""
    print("\n2. Тестируем /api/v1/auth/me...")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)

    print(f"   Статус: {response.status_code}")

    if response.status_code == 200:
        user_info = response.json()
        print(f"   Успех! Информация о пользователе:")
        print(f"   - Имя: {user_info.get('full_name')}")
        print(f"   - Роль: {user_info.get('role')}")
        print(f"   - Активен: {user_info.get('is_active')}")
    else:
        print(f"   Ошибка: {response.text}")


def test_patients_endpoint(token):
    """Тест endpoint /patients"""
    print("\n3. Тестируем /api/v1/patients...")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(f"{BASE_URL}/api/v1/patients/", headers=headers)

    print(f"   Статус: {response.status_code}")

    if response.status_code == 200:
        patients = response.json()
        print(f"   Успех! Найдено пациентов: {len(patients)}")
        if patients:
            print(f"   Первый пациент: {patients[0].get('last_name')}")
    else:
        print(f"   Ошибка: {response.text}")


def test_health_endpoint():
    """Тест endpoint /health"""
    print("\n4. Тестируем /api/v1/health...")

    response = requests.get(f"{BASE_URL}/api/v1/health")

    print(f"   Статус: {response.status_code}")

    if response.status_code == 200:
        health = response.json()
        print(f"   Статус: {health.get('status')}")
        print(f"   База данных: {health.get('database')}")
    else:
        print(f"   Ошибка: {response.text}")


def main():
    """Основная функция тестирования"""
    print("=" * 50)
    print("Тестирование аутентификации ReUnityHandler")
    print("=" * 50)

    # Тестируем endpoint health (должен работать без токена)
    test_health_endpoint()

    # Тестируем вход
    token = test_login()

    if token:
        # Тестируем endpoint /me
        test_me_endpoint(token)

        # Тестируем endpoint /patients
        test_patients_endpoint(token)
    else:
        print("\n❌ Не удалось получить токен. Проверьте:")
        print("   - Запущен ли сервер?")
        print("   - Правильные ли данные в .env файле?")
        print("   - Созданы ли пользователи в базе данных?")


if __name__ == "__main__":
    main()