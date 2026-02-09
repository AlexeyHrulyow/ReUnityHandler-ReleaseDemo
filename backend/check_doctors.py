# check_doctors.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from reunity_app.db.session import AsyncSessionLocal
from reunity_app.db.models import Doctor
from sqlalchemy import select


async def check_doctors():
    async with AsyncSessionLocal() as session:
        print("👨‍⚕️ Проверяем врачей в базе данных...")

        result = await session.execute(select(Doctor))
        doctors = result.scalars().all()

        print(f"Всего врачей: {len(doctors)}")

        for doc in doctors:
            print(f"\nВрач ID: {doc.id}")
            print(f"  Имя пользователя: {doc.username}")
            print(f"  ФИО: {doc.full_name}")
            print(f"  Роль: {doc.role}")
            print(f"  Активен: {doc.is_active}")
            print(f"  Пароль (хеш): {doc.hashed_password[:20]}...")


if __name__ == "__main__":
    asyncio.run(check_doctors())