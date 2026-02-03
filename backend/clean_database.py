import asyncio
import asyncpg
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))

from reunity_app.core.config import settings


async def clean_database():
    """Очистка базы данных от старых таблиц"""
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))

        # Получаем список таблиц
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        if tables:
            print("🗑️  Удаляю старые таблицы...")

            # Удаляем в правильном порядке (с учётом foreign keys)
            drop_order = [
                'webmis_field_mapping',
                'document_sections',
                'documents',
                'document_templates',
                'cases',
                'doctors',
                'patients'
            ]

            for table_name in drop_order:
                # Проверяем, существует ли таблица
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = $1)",
                    table_name
                )

                if exists:
                    await conn.execute(f'DROP TABLE "{table_name}" CASCADE')
                    print(f"  ✓ Удалена таблица: {table_name}")

            print("✅ База данных очищена")
        else:
            print("✅ В базе данных нет таблиц для удаления")

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")


if __name__ == "__main__":
    asyncio.run(clean_database())