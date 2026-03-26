from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Patient as PatientModel
from reunity_app.schemas.patient import PatientCreate, PatientUpdate, Patient as PatientSchema

router = APIRouter()


@router.post("/", response_model=PatientSchema)
async def create_patient(
        patient: PatientCreate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head", "therapist_frm", "neurologist_frm", "psychologist", "reflexotherapist", "physiotherapist"))
):
    """Создание нового пациента (доступно всем врачам)"""
    db_patient = PatientModel(**patient.dict())
    db.add(db_patient)
    await db.commit()
    await db.refresh(db_patient)

    return PatientSchema(
        id=db_patient.id,
        last_name=db_patient.last_name,
        first_name=db_patient.first_name,
        middle_name=db_patient.middle_name,
        birth_date=db_patient.birth_date,
        insurance_number=db_patient.insurance_number,
        created_at=db_patient.created_at
    )


@router.get("/", response_model=List[PatientSchema])
async def list_patients(
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = Query(None, description="Поиск по ФИО"),
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение списка пациентов с поиском (доступно всем авторизованным)"""
    query = select(PatientModel)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                PatientModel.last_name.ilike(search_term),
                PatientModel.first_name.ilike(search_term),
                PatientModel.middle_name.ilike(search_term)
            )
        )

    query = query.offset(skip).limit(limit).order_by(PatientModel.last_name, PatientModel.first_name)

    result = await db.execute(query)
    patients = result.scalars().all()

    return [
        PatientSchema(
            id=patient.id,
            last_name=patient.last_name,
            first_name=patient.first_name,
            middle_name=patient.middle_name,
            birth_date=patient.birth_date,
            insurance_number=patient.insurance_number,
            created_at=patient.created_at
        )
        for patient in patients
    ]


@router.get("/search", response_model=List[PatientSchema])
async def search_patients(
        q: str = Query(..., min_length=2, description="Строка поиска"),
        limit: int = 10,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Умный поиск пациентов по части ФИО (доступно всем авторизованным)"""
    search_term = f"%{q}%"

    query = select(PatientModel).where(
        or_(
            func.concat(PatientModel.last_name, ' ', PatientModel.first_name).ilike(search_term),
            func.concat(PatientModel.last_name, ' ', PatientModel.first_name, ' ', PatientModel.middle_name).ilike(search_term),
            PatientModel.last_name.ilike(search_term),
            PatientModel.first_name.ilike(search_term),
            PatientModel.insurance_number.ilike(search_term)
        )
    ).limit(limit)

    result = await db.execute(query)
    patients = result.scalars().all()

    return [
        PatientSchema(
            id=patient.id,
            last_name=patient.last_name,
            first_name=patient.first_name,
            middle_name=patient.middle_name,
            birth_date=patient.birth_date,
            insurance_number=patient.insurance_number,
            created_at=patient.created_at
        )
        for patient in patients
    ]


@router.get("/{patient_id}", response_model=PatientSchema)
async def get_patient(
        patient_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение информации о пациенте (доступно всем авторизованным)"""
    result = await db.execute(select(PatientModel).where(PatientModel.id == patient_id))
    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(status_code=404, detail="Пациент не найден")

    return PatientSchema(
        id=patient.id,
        last_name=patient.last_name,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        birth_date=patient.birth_date,
        insurance_number=patient.insurance_number,
        created_at=patient.created_at
    )


@router.put("/{patient_id}", response_model=PatientSchema)
async def update_patient(
        patient_id: int,
        patient_update: PatientUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head", "therapist_frm", "neurologist_frm", "psychologist", "reflexotherapist", "physiotherapist"))
):
    """Обновление информации о пациенте (доступно всем врачам)"""
    result = await db.execute(select(PatientModel).where(PatientModel.id == patient_id))
    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(status_code=404, detail="Пациент не найден")

    update_data = patient_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)

    return PatientSchema(
        id=patient.id,
        last_name=patient.last_name,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        birth_date=patient.birth_date,
        insurance_number=patient.insurance_number,
        created_at=patient.created_at
    )


@router.delete("/{patient_id}")
async def delete_patient(
        patient_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head"))
):
    """Удаление пациента (только для администратора и заведующего)"""
    result = await db.execute(select(PatientModel).where(PatientModel.id == patient_id))
    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(status_code=404, detail="Пациент не найден")

    await db.delete(patient)
    await db.commit()

    return {"message": "Пациент удален"}