import asyncio
import sys
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.append(str(Path(__file__).parent))


def create_tables_sync():
    """Синхронное создание таблиц"""
    from sqlalchemy import create_engine
    from reunity_app.core.config import settings
    from reunity_app.db.base import Base

    # Создаём синхронный движок
    sync_database_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_database_url)

    # ВАЖНО: ЯВНО импортируем ВСЕ модели
    from reunity_app.db.models import (
        Patient, Doctor, Case, Document,
        DocumentSection, DocumentTemplate, WebmisFieldMapping
    )

    # Создаём таблицы
    Base.metadata.create_all(engine)

    print("✅ Таблицы созданы успешно")

    # Проверяем, какие таблицы создались
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print("📋 Созданные таблицы:")
    for table in tables:
        print(f"  - {table}")

    engine.dispose()
    return tables


async def check_tables():
    """Проверяем, какие таблицы существуют"""
    import asyncpg

    from reunity_app.core.config import settings

    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))

    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)

    print("\n📋 Проверка через asyncpg:")
    if tables:
        for table in tables:
            print(f"  - {table['table_name']}")
    else:
        print("  📭 Таблицы отсутствуют")

    await conn.close()


async def main():
    print("=== Создание таблиц базы данных ===")

    try:
        # Создаём таблицы
        tables = create_tables_sync()

        # Проверяем результат
        await check_tables()

        print(f"\n🎉 Создано {len(tables)} таблиц:")
        for table in tables:
            print(f"  ✓ {table}")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())