import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from reunity_app.core.config import settings
from reunity_app.db.session import engine
from reunity_app.db.models import Doctor, Patient, Case, CaseStatus


async def create_test_case():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Получаем пациента
        result = await session.execute(select(Patient))
        patient = result.scalars().first()

        if not patient:
            print("❌ Нет пациентов в базе. Сначала запустите create_initial_data.py")
            return

        # Получаем врача (администратора)
        result = await session.execute(select(Doctor).where(Doctor.username == 'admin'))
        doctor = result.scalar_one_or_none()

        if not doctor:
            print("❌ Администратор не найден")
            return

        # Создаем случай
        case = Case(
            patient_id=patient.id,
            creator_id=doctor.id,
            admission_date=datetime.utcnow(),
            status=CaseStatus.DRAFT
        )

        session.add(case)
        await session.commit()
        await session.refresh(case)

        print(f"✅ Создан тестовый случай ID: {case.id}")
        print(f"   Пациент: {patient.full_name}")
        print(f"   Врач: {doctor.full_name}")


async def main():
    print("=== Создание тестового случая ===")
    await create_test_case()


if __name__ == "__main__":
    asyncio.run(main())