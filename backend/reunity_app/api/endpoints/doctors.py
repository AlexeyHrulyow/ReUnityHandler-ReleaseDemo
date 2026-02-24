from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from reunity_app.core.security import get_current_active_user, require_role, get_password_hash
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor as DoctorModel, DoctorRole
from reunity_app.schemas.doctor import DoctorCreate, DoctorUpdate, Doctor as DoctorSchema, SetPasswordRequest   # ИЗМЕНЕНО: импорт SetPasswordRequest

router = APIRouter()


@router.get("/", response_model=List[DoctorSchema])
async def list_doctors(
        skip: int = 0,
        limit: int = 100,
        role: Optional[DoctorRole] = None,
        active_only: bool = True,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(require_role("admin", "head"))
):
    """Получение списка врачей (только для админа и заведующего)"""
    query = select(DoctorModel)

    if active_only:
        query = query.where(DoctorModel.is_active == True)

    if role:
        query = query.where(DoctorModel.role == role)

    query = query.offset(skip).limit(limit).order_by(DoctorModel.last_name, DoctorModel.first_name)

    result = await db.execute(query)
    doctors = result.scalars().all()

    # Преобразуем модели в схемы
    return [
        DoctorSchema(
            id=doctor.id,
            username=doctor.username,
            last_name=doctor.last_name,
            first_name=doctor.first_name,
            middle_name=doctor.middle_name,
            role=doctor.role,
            is_active=doctor.is_active,
            created_at=doctor.created_at
        )
        for doctor in doctors
    ]


@router.post("/", response_model=DoctorSchema)
async def create_doctor(
        doctor: DoctorCreate,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(require_role("admin"))
):
    """Создание нового врача (только для админа)"""
    # Проверяем уникальность username
    result = await db.execute(select(DoctorModel).where(DoctorModel.username == doctor.username))
    existing_doctor = result.scalar_one_or_none()

    if existing_doctor:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким именем уже существует"
        )

    # Создаем врача
    hashed_password = get_password_hash(doctor.password)
    db_doctor = DoctorModel(
        username=doctor.username,
        hashed_password=hashed_password,
        last_name=doctor.last_name,
        first_name=doctor.first_name,
        middle_name=doctor.middle_name,
        role=doctor.role,
        is_active=True
    )

    db.add(db_doctor)
    await db.commit()
    await db.refresh(db_doctor)

    # Возвращаем объект схемы
    return DoctorSchema(
        id=db_doctor.id,
        username=db_doctor.username,
        last_name=db_doctor.last_name,
        first_name=db_doctor.first_name,
        middle_name=db_doctor.middle_name,
        role=db_doctor.role,
        is_active=db_doctor.is_active,
        created_at=db_doctor.created_at
    )


@router.get("/{doctor_id}", response_model=DoctorSchema)
async def get_doctor(
        doctor_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(require_role("admin", "head"))
):
    """Получение информации о враче (только для админа и заведующего)"""
    result = await db.execute(select(DoctorModel).where(DoctorModel.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=404, detail="Врач не найден")

    # Возвращаем объект схемы
    return DoctorSchema(
        id=doctor.id,
        username=doctor.username,
        last_name=doctor.last_name,
        first_name=doctor.first_name,
        middle_name=doctor.middle_name,
        role=doctor.role,
        is_active=doctor.is_active,
        created_at=doctor.created_at
    )


@router.put("/{doctor_id}", response_model=DoctorSchema)
async def update_doctor(
        doctor_id: int,
        doctor_update: DoctorUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(require_role("admin"))
):
    """Обновление информации о враче (только для админа)"""
    result = await db.execute(select(DoctorModel).where(DoctorModel.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=404, detail="Врач не найден")

    # Нельзя редактировать самого себя через этот эндпоинт
    if doctor.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Используйте профиль для редактирования собственных данных"
        )

    # Обновляем поля
    update_data = doctor_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doctor, field, value)

    await db.commit()
    await db.refresh(doctor)

    # Возвращаем объект схемы
    return DoctorSchema(
        id=doctor.id,
        username=doctor.username,
        last_name=doctor.last_name,
        first_name=doctor.first_name,
        middle_name=doctor.middle_name,
        role=doctor.role,
        is_active=doctor.is_active,
        created_at=doctor.created_at
    )


@router.delete("/{doctor_id}")
async def delete_doctor(
        doctor_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(require_role("admin"))
):
    """Удаление врача (только для админа)"""
    result = await db.execute(select(DoctorModel).where(DoctorModel.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=404, detail="Врач не найден")

    # Нельзя удалить самого себя
    if doctor.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить собственный аккаунт"
        )

    await db.delete(doctor)
    await db.commit()

    return {"message": "Врач удален"}


@router.post("/{doctor_id}/activate")
async def activate_doctor(
        doctor_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(require_role("admin", "head"))
):
    """Активация врача (только для админа и заведующего)"""
    result = await db.execute(select(DoctorModel).where(DoctorModel.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=404, detail="Врач не найден")

    doctor.is_active = True
    await db.commit()

    return {"message": "Врач активирован"}


@router.post("/{doctor_id}/deactivate")
async def deactivate_doctor(
        doctor_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(require_role("admin", "head"))
):
    """Деактивация врача (только для админа и заведующего)"""
    result = await db.execute(select(DoctorModel).where(DoctorModel.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=404, detail="Врач не найден")

    # Нельзя деактивировать самого себя
    if doctor.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Нельзя деактивировать собственный аккаунт"
        )

    doctor.is_active = False
    await db.commit()

    return {"message": "Врач деактивирован"}


# ИЗМЕНЕНО: новый эндпоинт для смены пароля врача администратором
@router.post("/{doctor_id}/set-password")
async def set_doctor_password(
        doctor_id: int,
        password_data: SetPasswordRequest,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(require_role("admin"))
):
    """Установка нового пароля для врача (только для админа)"""
    result = await db.execute(select(DoctorModel).where(DoctorModel.id == doctor_id))
    doctor = result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=404, detail="Врач не найден")

    doctor.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "Пароль успешно изменен"}