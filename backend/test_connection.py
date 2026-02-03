import asyncio
import asyncpg
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.append(str(Path(__file__).parent))

from reunity_app.core.config import settings
from reunity_app.db.session import engine


async def test_database():
    """Тестируем подключение к базе данных"""
    try:
        # Проверяем подключение с помощью asyncpg напрямую
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
        print("✅ Подключение к PostgreSQL успешно")
        await conn.close()

        # Проверяем подключение через SQLAlchemy
        async with engine.connect() as conn:
            print("✅ SQLAlchemy подключение успешно")

        return True

    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        print(f"URL базы данных: {settings.DATABASE_URL}")
        return False


async def test_config():
    """Тестируем загрузку конфигурации"""
    try:
        from reunity_app.core.config import settings
        print(f"✅ Конфигурация загружена")
        print(f"  APP_NAME: {settings.APP_NAME}")
        print(f"  DEBUG: {settings.DEBUG}")
        print(f"  DATABASE_URL: {settings.DATABASE_URL[:30]}...")
        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False


async def main():
    print("=== Тестирование ReUnityHandler ===")

    print("\n1. Тестирование конфигурации...")
    config_ok = await test_config()

    print("\n2. Тестирование подключения к базе данных...")
    db_ok = await test_database()

    print("\n=== Результаты ===")
    if config_ok and db_ok:
        print("✅ Все тесты пройдены успешно!")
        print("\nЗапустите сервер командой:")
        print("uvicorn reunity_app.main:reunity_app --reload --host 0.0.0.0 --port 8000")
    else:
        print("❌ Есть проблемы с настройкой проекта")
        print("\nПроверьте:")
        print("1. Файл .env существует и содержит правильные данные")
        print("2. PostgreSQL запущен и доступен")
        print("3. База данных 'reunityhandler' существует")


if __name__ == "__main__":
    asyncio.run(main())