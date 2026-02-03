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

        # Получаем список таблиц
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
            print("📋 Таблицы в базе данных:")
            print("-" * 50)
            for table in tables:
                print(f"📁 {table['table_name']} ({table['column_count']} столбцов)")
        else:
            print("📭 В базе данных нет таблиц")

        # Получаем общую статистику
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as table_count,
                SUM((SELECT COUNT(*) FROM information_schema.columns 
                     WHERE table_schema = 'public' AND table_name = t.table_name)) as total_columns
            FROM information_schema.tables t
            WHERE table_schema = 'public';
        """)

        print("-" * 50)
        print(f"📊 Всего таблиц: {stats['table_count']}")
        print(f"📊 Всего столбцов: {stats['total_columns']}")

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(check_database_tables())