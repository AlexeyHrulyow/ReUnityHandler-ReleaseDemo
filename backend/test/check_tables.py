import asyncio
import asyncpg
from pathlib import Path
import sys

# Добавляем родительскую директорию в путь
sys.path.append(str(Path(__file__).parent))

from reunity_app.core.config import settings


async def check_database_tables():
    """Проверяем, какие таблицы существуют в базе данных"""
    try:
        # Подключаемся напрямую через asyncpg
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))

        print("📋 Проверка существующих таблиц...")

        # Проверяем, есть ли старые таблицы
        tables = await conn.fetch("""
            SELECT 
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns 
                 WHERE table_schema = 'public' AND table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        if tables:
            print("📋 Существующие таблицы:")
            print("-" * 50)
            for table in tables:
                print(f"📁 {table['table_name']} ({table['column_count']} столбцов)")
        else:
            print("📭 В базе данных нет таблиц")

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(check_database_tables())