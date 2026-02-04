import asyncio
import sys
from pathlib import Path
from datetime import datetime, date
import hashlib

sys.path.append(str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from reunity_app.core.config import settings
from reunity_app.db.session import engine
from reunity_app.db.models import Doctor, DoctorRole, Patient


# Простая функция хеширования пароля для тестирования
def get_password_hash(password: str) -> str:
    # Используем SHA256 для простоты (в продакшене нужен bcrypt или argon2)
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


async def create_initial_data():
    """Создание начальных данных в базе"""

    # Создаем асинхронную сессию
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Создаем администратора
        result = await session.execute(
            select(Doctor).where(Doctor.username == 'admin')
        )
        admin_doctor_exists = result.scalar_one_or_none()

        if not admin_doctor_exists:
            admin_doctor = Doctor(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                last_name="Администратор",
                first_name="Системный",
                middle_name="",
                role=DoctorRole.ADMIN,
                is_active=True
            )
            session.add(admin_doctor)
            print("✅ Создан администратор: admin / admin123")

        # Создаем заведующего отделением
        result = await session.execute(
            select(Doctor).where(Doctor.username == 'head')
        )
        head_doctor_exists = result.scalar_one_or_none()

        if not head_doctor_exists:
            head_doctor = Doctor(
                username="head",
                hashed_password=get_password_hash("head123"),
                last_name="Иванов",
                first_name="Петр",
                middle_name="Сергеевич",
                role=DoctorRole.HEAD,
                is_active=True
            )
            session.add(head_doctor)
            print("✅ Создан заведующий: head / head123")

        # Создаем невролога
        result = await session.execute(
            select(Doctor).where(Doctor.username == 'neuro')
        )
        neuro_doctor_exists = result.scalar_one_or_none()

        if not neuro_doctor_exists:
            neuro_doctor = Doctor(
                username="neuro",
                hashed_password=get_password_hash("neuro123"),
                last_name="Петрова",
                first_name="Анна",
                middle_name="Владимировна",
                role=DoctorRole.NEUROLOGIST,
                is_active=True
            )
            session.add(neuro_doctor)
            print("✅ Создан невролог: neuro / neuro123")

        # Создаем терапевта
        result = await session.execute(
            select(Doctor).where(Doctor.username == 'therapist')
        )
        therapist_doctor_exists = result.scalar_one_or_none()

        if not therapist_doctor_exists:
            therapist_doctor = Doctor(
                username="therapist",
                hashed_password=get_password_hash("therapy123"),
                last_name="Сидоров",
                first_name="Алексей",
                middle_name="Михайлович",
                role=DoctorRole.THERAPIST,
                is_active=True
            )
            session.add(therapist_doctor)
            print("✅ Создан терапевт: therapist / therapy123")

        # Создаем тестовых пациентов
        test_patients_data = [
            {
                "last_name": "Смирнов",
                "first_name": "Иван",
                "middle_name": "Петрович",
                "birth_date": date(1965, 5, 15),
                "insurance_number": "1234"
            },
            {
                "last_name": "Кузнецова",
                "first_name": "Мария",
                "middle_name": "Сергеевна",
                "birth_date": date(1978, 8, 22),
                "insurance_number": "5678"
            },
            {
                "last_name": "Попов",
                "first_name": "Дмитрий",
                "middle_name": "Александрович",
                "birth_date": date(1955, 12, 3),
                "insurance_number": "9012"
            }
        ]

        for patient_data in test_patients_data:
            # Проверяем существование пациента
            result = await session.execute(
                select(Patient).where(
                    Patient.last_name == patient_data["last_name"],
                    Patient.first_name == patient_data["first_name"],
                    Patient.middle_name == patient_data["middle_name"]
                )
            )
            existing_patient = result.scalar_one_or_none()

            if not existing_patient:
                patient = Patient(**patient_data)
                session.add(patient)
                print(f"✅ Создан пациент: {patient.last_name} {patient.first_name}")

        await session.commit()
        print("\n🎉 Начальные данные успешно созданы!")


async def main():
    print("=== Создание начальных данных ===")
    try:
        await create_initial_data()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())