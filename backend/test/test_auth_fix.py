#!/usr/bin/env python3
"""
Скрипт для тестирования исправленной аутентификации
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"


def print_step(step):
    print(f"\n{'=' * 60}")
    print(f"ШАГ {step}")
    print('=' * 60)


def test_health():
    """Тест endpoint /health"""
    print_step("1: Тестирование /health")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"   Статус: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Успех: {data.get('status')}")
            print(f"   База данных: {data.get('database')}")
            return True
        else:
            print(f"   ❌ Ошибка: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return False


def test_api_health():
    """Тест endpoint /api/v1/health"""
    print_step("2: Тестирование /api/v1/health")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        print(f"   Статус: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Успех: {data.get('status')}")
            print(f"   База данных: {data.get('database')}")
            print(f"   Версия API: {data.get('api_version')}")
            return True
        else:
            print(f"   ❌ Ошибка: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return False


def test_login(username, password):
    """Тест входа в систему"""
    print_step(f"3: Тестирование входа для пользователя '{username}'")
    try:
        form_data = {
            'username': username,
            'password': password
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            data=form_data,
            timeout=10
        )

        print(f"   Статус: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print(f"   ✅ Успех! Токен получен")
            print(f"   Тип токена: {data.get('token_type')}")
            print(f"   Длина токена: {len(token)} символов")
            return token
        else:
            error_text = response.text
            print(f"   ❌ Ошибка: {error_text}")
            return None
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return None


def test_me_endpoint(token):
    """Тест endpoint /me"""
    print_step("4: Тестирование /api/v1/auth/me")
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=headers,
            timeout=5
        )

        print(f"   Статус: {response.status_code}")

        if response.status_code == 200:
            user_info = response.json()
            print(f"   ✅ Успех! Информация о пользователе:")
            print(f"   - ID: {user_info.get('id')}")
            print(f"   - Имя пользователя: {user_info.get('username')}")
            print(f"   - Полное имя: {user_info.get('full_name')}")
            print(f"   - Роль: {user_info.get('role')}")
            print(f"   - Активен: {user_info.get('is_active')}")
            return user_info
        else:
            error_text = response.text
            print(f"   ❌ Ошибка: {error_text}")
            return None
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return None


def test_patients_endpoint(token):
    """Тест endpoint /patients"""
    print_step("5: Тестирование /api/v1/patients")
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/patients/",
            headers=headers,
            timeout=5
        )

        print(f"   Статус: {response.status_code}")

        if response.status_code == 200:
            patients = response.json()
            print(f"   ✅ Успех! Найдено пациентов: {len(patients)}")
            if patients:
                print(f"   Первый пациент: {patients[0].get('last_name')} {patients[0].get('first_name')}")
            return patients
        else:
            error_text = response.text
            print(f"   ❌ Ошибка: {error_text}")
            return None
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return None


def test_cases_endpoint(token):
    """Тест endpoint /cases"""
    print_step("6: Тестирование /api/v1/cases")
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/cases/",
            headers=headers,
            timeout=5
        )

        print(f"   Статус: {response.status_code}")

        if response.status_code == 200:
            cases = response.json()
            print(f"   ✅ Успех! Найдено случаев: {len(cases)}")
            if cases:
                print(f"   Первый случай: ID {cases[0].get('id')}, статус {cases[0].get('status')}")
            return cases
        else:
            error_text = response.text
            print(f"   ❌ Ошибка: {error_text}")
            return None
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return None


def test_tables_endpoint(token):
    """Тест endpoint /tables"""
    print_step("7: Тестирование /api/v1/tables")
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        response = requests.get(
            f"{BASE_URL}/api/v1/tables",
            headers=headers,
            timeout=5
        )

        print(f"   Статус: {response.status_code}")

        if response.status_code == 200:
            tables_data = response.json()
            print(f"   ✅ Успех! Найдено таблиц: {tables_data.get('count')}")
            tables = tables_data.get('tables', [])
            print(f"   Таблицы: {', '.join(tables)}")
            return tables
        else:
            error_text = response.text
            print(f"   ❌ Ошибка: {error_text}")
            return None
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
        return None


def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ АУТЕНТИФИКАЦИИ REUNITYHANDLER")
    print("=" * 60)

    # Тестируем открытые endpoints
    if not test_health():
        print("\n❌ Сервер не отвечает на /health")
        return

    if not test_api_health():
        print("\n❌ API не отвечает на /api/v1/health")
        return

    # Тестируем вход
    test_users = [
        ("admin", "admin123"),
        ("head", "head123"),
        ("neuro", "neuro123"),
        ("therapist", "therapy123")
    ]

    token = None
    user_info = None

    for username, password in test_users:
        token = test_login(username, password)
        if token:
            print(f"\n✅ Успешный вход для пользователя '{username}'")

            # Тестируем защищенные endpoints
            user_info = test_me_endpoint(token)
            if user_info:
                print(f"\n✅ Пользователь '{username}' успешно аутентифицирован")

                # Тестируем другие endpoints
                patients = test_patients_endpoint(token)
                cases = test_cases_endpoint(token)
                tables = test_tables_endpoint(token)

                # Сохраняем токен в файл для использования в браузере
                with open('test_token.txt', 'w') as f:
                    f.write(token)
                print(f"\n📝 Токен сохранен в файл test_token.txt")
                print("   Используйте его в браузере через консоль разработчика:")
                print(f"   localStorage.setItem('auth_token', '{token[:50]}...')")

                break
            else:
                print(f"\n❌ Ошибка аутентификации для пользователя '{username}'")
                token = None
        else:
            print(f"\n❌ Не удалось войти для пользователя '{username}'")

    if not token:
        print("\n❌ НЕ УДАЛОСЬ ПРОЙТИ АУТЕНТИФИКАЦИЮ")
        print("\nПроверьте:")
        print("1. Сервер запущен? (python run.py)")
        print("2. База данных создана? (reunityhandler)")
        print("3. Пользователи созданы? (python create_initial_data.py)")
        print("4. Пароли обновлены? (python update_passwords.py)")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 60)
    print("\nСледующие шаги:")
    print("1. Откройте браузер: http://localhost:8000")
    print("2. Войдите с данными одного из тестовых пользователей")
    print("3. Проверьте работу страниц /dashboard, /cases, /patients")
    print("\nЕсли остаются проблемы:")
    print("1. Очистите localStorage браузера")
    print("2. Используйте режим инкогнито")
    print("3. Проверьте консоль разработчика (F12)")


if __name__ == "__main__":
    main()