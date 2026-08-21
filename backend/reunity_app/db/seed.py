# reunity_app/db/seed.py
import logging
from sqlalchemy import select
from reunity_app.db.session import AsyncSessionLocal
from reunity_app.db.models import Doctor, DoctorRole
from reunity_app.core.security import get_password_hash

logger = logging.getLogger(__name__)

async def create_admin_if_not_exists():
    """Создаёт администратора, если его ещё нет."""
    async with AsyncSessionLocal() as session:
        # Проверяем наличие любого пользователя с ролью admin
        stmt = select(Doctor).where(Doctor.role == DoctorRole.ADMIN.value)
        result = await session.execute(stmt)
        admin = result.scalars().first()

        if admin:
            logger.info("Администратор уже существует (username: %s)", admin.username)
            return

        # Создаём нового администратора
        new_admin = Doctor(
            username="admin",
            hashed_password=get_password_hash("1234"),  # пароль по умолчанию
            role=DoctorRole.ADMIN.value,
            last_name="Администратор",
            first_name="Системы",
            middle_name=None,
            is_active=True,
            show_in_status=False,   # не показывать в статусах врачей
            status_order=0
        )
        session.add(new_admin)
        await session.commit()
        logger.info("✅ Администратор успешно создан: admin / 1234")