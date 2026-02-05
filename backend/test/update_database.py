#!/usr/bin/env python3
"""
Скрипт для обновления структуры базы данных
"""
import asyncio
from sqlalchemy import text
from reunity_app.db.session import engine


async def update_database():
    """Обновление структуры базы данных"""
    print("🔄 Обновление структуры базы данных...")

    async with engine.begin() as conn:
        try:
            # 1. Добавляем поле notes в таблицу cases, если его нет
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='cases' AND column_name='notes'
            """))

            if result.fetchone() is None:
                await conn.execute(text("ALTER TABLE cases ADD COLUMN notes TEXT"))
                print("✅ Добавлено поле 'notes' в таблицу 'cases'")
            else:
                print("✅ Поле 'notes' уже существует в таблице 'cases'")

            # 2. Проверяем наличие всех необходимых таблиц
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))

            tables = [row[0] for row in result.fetchall()]
            required_tables = [
                'patients', 'doctors', 'cases', 'documents',
                'document_sections', 'document_templates', 'webmis_field_mapping'
            ]

            for table in required_tables:
                if table in tables:
                    print(f"✅ Таблица '{table}' существует")
                else:
                    print(f"⚠️ Таблица '{table}' отсутствует")

            print("\n✅ Обновление базы данных завершено!")

        except Exception as e:
            print(f"❌ Ошибка при обновлении базы данных: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(update_database())