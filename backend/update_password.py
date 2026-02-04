#!/usr/bin/env python3
"""
Скрипт для обновления паролей в базе данных
"""
import asyncio
import hashlib
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from reunity_app.core.config import settings

# Тестовые пароли для пользователей
TEST_PASSWORDS = {
    "admin": "admin123",
    "head": "head123",
    "neuro": "neuro123",
    "therapist": "therapy123"
}


async def update_passwords():
    """Обновление паролей в базе данных"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        from reunity_app.db.models import Doctor

        # Получаем всех врачей
        result = await session.execute(select(Doctor))
        doctors = result.scalars().all()

        updated_count = 0
        for doctor in doctors:
            if doctor.username in TEST_PASSWORDS:
                # Хешируем пароль
                hashed_password = hashlib.sha256(TEST_PASSWORDS[doctor.username].encode()).hexdigest()

                # Обновляем пароль
                await session.execute(
                    update(Doctor)
                    .where(Doctor.id == doctor.id)
                    .values(hashed_password=hashed_password)
                )
                print(f"✅ Обновлен пароль для {doctor.username}")
                updated_count += 1

        await session.commit()
        print(f"\n✅ Обновлено {updated_count} паролей")


if __name__ == "__main__":
    asyncio.run(update_passwords())