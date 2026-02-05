#!/usr/bin/env python3
"""
Диагностика структуры базы данных
"""
import asyncio
from sqlalchemy import text
from reunity_app.db.session import engine


async def diagnose_database():
    """Диагностика базы данных"""
    print("🔍 Диагностика базы данных...")

    async with engine.connect() as conn:
        # 1. Проверяем подключение
        try:
            await conn.execute(text("SELECT 1"))
            print("✅ Подключение к базе данных успешно")
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return

        # 2. Проверяем таблицы
        print("\n📊 Таблицы в базе данных:")
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        )
        tables = [row[0] for row in result.fetchall()]

        for table in tables:
            print(f"  - {table}")

            # Проверяем структуру каждой таблицы
            columns_result = await conn.execute(
                text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """)
            )

            columns = columns_result.fetchall()
            for col in columns:
                print(f"    * {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")

        # 3. Проверяем конкретно таблицу cases
        print("\n🔎 Детальная проверка таблицы 'cases':")
        result = await conn.execute(
            text("""
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    CASE WHEN pk.column_name IS NOT NULL THEN 'PK' ELSE '' END as primary_key
                FROM information_schema.columns c
                LEFT JOIN (
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = 'cases' AND tc.constraint_type = 'PRIMARY KEY'
                ) pk ON c.column_name = pk.column_name
                WHERE c.table_name = 'cases'
                ORDER BY c.ordinal_position
            """)
        )

        columns_info = result.fetchall()
        print("   Структура таблицы 'cases':")
        for col in columns_info:
            pk_mark = f" [{col[3]}]" if col[3] else ""
            print(f"   - {col[0]}: {col[1]}{pk_mark} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")

        # 4. Проверяем данные
        print("\n📈 Количество записей в таблицах:")
        for table in tables:
            count_result = await conn.execute(
                text(f"SELECT COUNT(*) as count FROM {table}")
            )
            count = count_result.fetchone()[0]
            print(f"   - {table}: {count} записей")

        print("\n✅ Диагностика завершена")


if __name__ == "__main__":
    asyncio.run(diagnose_database())