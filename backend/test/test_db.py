import asyncio
from reunity_app.core.config import settings
from reunity_app.db.session import engine
from sqlalchemy import text


async def test_db():
    print(f"Подключение к: {settings.DATABASE_URL}")

    try:
        async with engine.connect() as conn:
            # Проверка таблиц
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))

            tables = [row[0] for row in result.fetchall()]
            print(f"Таблицы в базе: {tables}")

            # Проверка пациентов
            result = await conn.execute(text("SELECT COUNT(*) FROM patients"))
            patient_count = result.scalar()
            print(f"Пациентов: {patient_count}")

            # Проверка врачей
            result = await conn.execute(text("SELECT COUNT(*) FROM doctors"))
            doctor_count = result.scalar()
            print(f"Врачей: {doctor_count}")

            # Проверка случаев
            result = await conn.execute(text("SELECT COUNT(*) FROM cases"))
            case_count = result.scalar()
            print(f"Случаев: {case_count}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")


asyncio.run(test_db())