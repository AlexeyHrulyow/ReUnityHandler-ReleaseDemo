import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from reunity_app.core.security import verify_password, get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from reunity_app.db.session import engine
from reunity_app.db.models import Doctor


async def test_login():
    """Тестирование логина"""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            select(Doctor).where(Doctor.username == 'admin')
        )
        doctor = result.scalar_one_or_none()

        if doctor:
            print(f"Найден пользователь: {doctor.username}")
            print(f"Хеш в базе: {doctor.hashed_password}")

            # Проверяем пароль
            test_passwords = ["admin123", "wrongpassword"]
            for password in test_passwords:
                is_valid = verify_password(password, doctor.hashed_password)
                print(f"Пароль '{password}': {'✅ ВЕРНЫЙ' if is_valid else '❌ НЕВЕРНЫЙ'}")
        else:
            print("❌ Пользователь admin не найден")


async def main():
    print("=== Тестирование аутентификации ===")
    await test_login()


if __name__ == "__main__":
    asyncio.run(main())