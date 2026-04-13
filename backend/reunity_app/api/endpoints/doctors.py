from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from reunity_app.core.security import get_current_active_user, require_role, get_password_hash
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor as DoctorModel, DoctorRole
from reunity_app.schemas.doctor import DoctorCreate, DoctorUpdate, Doctor as DoctorSchema, SetPasswordRequest

router = APIRouter()


async def ensure_unique_active_for_role(db: AsyncSession, role: DoctorRole, exclude_id: int = None) -> Optional[DoctorModel]:
    """
    Проверяет, есть ли активный врач для данной роли, исключая врача с exclude_id.
    Возвращает найденного врача, если есть, иначе None.
    """
    query = select(DoctorModel).where(
        DoctorModel.role == role,
        DoctorModel.is_active == True
    )
    if exclude_id:
        query = query.where(DoctorModel.id != exclude_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

@router.put("/status-settings")
async def update_status_settings(
    settings: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    current_user: DoctorModel = Depends(require_role("admin"))
):
    """Обновить настройки отображения врачей в статусах."""
    for item in settings:
        result = await db.execute(
            select(DoctorModel).where(DoctorModel.id == item["id"])
        )
        doctor = result.scalar_one_or_none()
        if doctor:
            doctor.show_in_status = item.get("show_in_status", doctor.show_in_status)
            doctor.status_order = item.get("status_order", doctor.status_order)
    await db.commit()
    return {"message": "Настройки сохранены"}

@router.get("/", response_model=List[DoctorSchema])
async def list_doctors(
        skip: int = 0,
        limit: int = 100,
        role: Optional[DoctorRole] = None,
        active_only: bool = True,
        db: AsyncSession = Depends(get_db),
        current_user: DoctorModel = Depends(get_current_active_user)
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
        raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует")

    # Проверяем, есть ли уже активный врач с такой ролью
    active_for_role = await ensure_unique_active_for_role(db, doctor.role)
    # Если есть активный, создаём неактивного, иначе активного
    is_active = (active_for_role is None)

    hashed_password = get_password_hash(doctor.password)
    db_doctor = DoctorModel(
        username=doctor.username,
        hashed_password=hashed_password,
        last_name=doctor.last_name,
        first_name=doctor.first_name,
        middle_name=doctor.middle_name,
        role=doctor.role,
        is_active=is_active
    )

    db.add(db_doctor)
    await db.commit()
    await db.refresh(db_doctor)

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

    update_data = doctor_update.dict(exclude_unset=True)

    # Если изменяется username, проверить уникальность
    if "username" in update_data and update_data["username"] != doctor.username:
        # Проверить, что такой username не занят другим врачом
        result_username = await db.execute(
            select(DoctorModel).where(DoctorModel.username == update_data["username"])
        )
        existing = result_username.scalar_one_or_none()
        if existing and existing.id != doctor_id:
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким именем уже существует"
            )

    # Если изменяется роль
    if "role" in update_data and update_data["role"] != doctor.role:
        new_role = update_data["role"]
        # Если текущий врач активен, нужно проверить, не появится ли второй активный с новой ролью
        if doctor.is_active:
            active_for_role = await ensure_unique_active_for_role(db, new_role, exclude_id=doctor.id)
            if active_for_role:
                raise HTTPException(
                    status_code=400,
                    detail=f"Для роли {new_role} уже есть активный врач: {active_for_role.full_name}. "
                           f"Сначала деактивируйте его или измените роль на неактивную."
                )
        # Если врач неактивен, то ничего страшного – новый активный не появится
        # (но если он станет активным позже, проверка будет при активации)

    # Если изменяется поле is_active (через этот эндпоинт это тоже возможно)
    # Но лучше использовать отдельные эндпоинты activate/deactivate.
    # Оставим здесь базовое обновление без автоматической смены активности,
    # но если is_active передано True и есть другой активный для этой роли – ошибка.
    if "is_active" in update_data and update_data["is_active"] and not doctor.is_active:
        # Пытаемся активировать врача
        active_for_role = await ensure_unique_active_for_role(db, doctor.role, exclude_id=doctor.id)
        if active_for_role:
            raise HTTPException(
                status_code=400,
                detail=f"Нельзя активировать врача, так как для роли {doctor.role} уже есть активный: {active_for_role.full_name}. "
                       f"Используйте кнопку активации для деактивации другого."
            )

    for field, value in update_data.items():
        setattr(doctor, field, value)

    await db.commit()
    await db.refresh(doctor)

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

    if doctor.is_active:
        return {"message": "Врач уже активен"}

    # Проверяем, есть ли другой активный с такой же ролью
    active_for_role = await ensure_unique_active_for_role(db, doctor.role, exclude_id=doctor.id)
    if active_for_role:
        # Автоматически деактивируем другого
        active_for_role.is_active = False
        db.add(active_for_role)

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

    if not doctor.is_active:
        return {"message": "Врач уже неактивен"}

    doctor.is_active = False
    await db.commit()

    return {"message": "Врач деактивирован"}


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

@router.get("/status-doctors")
async def get_status_doctors(
    db: AsyncSession = Depends(get_db),
    current_user: DoctorModel = Depends(require_role("admin"))
):
    """Получить список врачей для настройки отображения в статусах."""
    result = await db.execute(
        select(DoctorModel)
        .where(DoctorModel.is_active == True)
        .order_by(DoctorModel.status_order, DoctorModel.id)
    )
    doctors = result.scalars().all()
    return [
        {
            "id": d.id,
            "full_name": d.full_name,
            "role": d.role,
            "show_in_status": d.show_in_status,
            "status_order": d.status_order
        }
        for d in doctors
    ]