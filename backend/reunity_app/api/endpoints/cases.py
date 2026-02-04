from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from datetime import datetime

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Patient, Case as CaseModel, Document, CaseStatus, DoctorRole
from reunity_app.schemas.case import CaseCreate, CaseUpdate, Case as CaseSchema, CaseWithPatient

router = APIRouter()


@router.post("/", response_model=CaseSchema)
async def create_case(
        case: CaseCreate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Создание нового случая"""
    # Проверяем существование пациента
    result = await db.execute(select(Patient).where(Patient.id == case.patient_id))
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Пациент не найден")

    # Создаем случай
    db_case = CaseModel(
        patient_id=case.patient_id,
        creator_id=current_user.id,
        admission_date=case.admission_date,
        status=case.status
    )

    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)

    # Создаем связанный документ
    db_document = Document(
        case_id=db_case.id,
        content={"sections": {}}
    )
    db.add(db_document)
    await db.commit()

    return db_case


@router.get("/", response_model=List[CaseWithPatient])
async def list_cases(
        skip: int = 0,
        limit: int = 100,
        status: Optional[CaseStatus] = Query(None, description="Фильтр по статусу"),
        patient_id: Optional[int] = Query(None, description="Фильтр по пациенту"),
        search: Optional[str] = Query(None, description="Поиск по ФИО пациента"),
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение списка случаев с фильтрацией"""
    query = select(CaseModel).join(Patient)

    # Применяем фильтры
    if status:
        query = query.where(CaseModel.status == status)

    if patient_id:
        query = query.where(CaseModel.patient_id == patient_id)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Patient.last_name.ilike(search_term),
                Patient.first_name.ilike(search_term),
                Patient.middle_name.ilike(search_term)
            )
        )

    # Врачи видят только свои случаи, админы и заведующие видят все
    if current_user.role not in [DoctorRole.ADMIN, DoctorRole.HEAD]:
        query = query.where(CaseModel.creator_id == current_user.id)

    query = query.offset(skip).limit(limit).order_by(CaseModel.created_at.desc())

    result = await db.execute(query)
    cases = result.scalars().all()

    # Формируем ответ с дополнительной информацией
    cases_with_details = []
    for case in cases:
        # Получаем информацию о пациенте
        patient_result = await db.execute(select(Patient).where(Patient.id == case.patient_id))
        patient = patient_result.scalar_one_or_none()

        # Получаем информацию о создателе
        creator_result = await db.execute(select(Doctor).where(Doctor.id == case.creator_id))
        creator = creator_result.scalar_one_or_none()

        # Создаем объект схемы
        case_data = CaseSchema(
            id=case.id,
            patient_id=case.patient_id,
            creator_id=case.creator_id,
            admission_date=case.admission_date,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
            completed_at=case.completed_at,
            sent_to_webmis_at=case.sent_to_webmis_at
        )

        # Преобразуем в CaseWithPatient
        case_with_patient = CaseWithPatient(
            **case_data.dict(),
            patient_name=patient.full_name if patient else "Неизвестно",
            patient_insurance=patient.insurance_number if patient else None,
            creator_name=creator.full_name if creator else "Неизвестно"
        )

        cases_with_details.append(case_with_patient)

    return cases_with_details


@router.get("/{case_id}", response_model=CaseWithPatient)
async def get_case(
        case_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение информации о конкретном случае"""
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    # Проверка прав доступа
    if current_user.role not in [DoctorRole.ADMIN, DoctorRole.HEAD] and case.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к данному случаю")

    # Получаем дополнительную информацию
    patient_result = await db.execute(select(Patient).where(Patient.id == case.patient_id))
    patient = patient_result.scalar_one_or_none()

    creator_result = await db.execute(select(Doctor).where(Doctor.id == case.creator_id))
    creator = creator_result.scalar_one_or_none()

    # Создаем объект схемы
    case_data = CaseSchema(
        id=case.id,
        patient_id=case.patient_id,
        creator_id=case.creator_id,
        admission_date=case.admission_date,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
        completed_at=case.completed_at,
        sent_to_webmis_at=case.sent_to_webmis_at
    )

    return CaseWithPatient(
        **case_data.dict(),
        patient_name=patient.full_name if patient else "Неизвестно",
        patient_insurance=patient.insurance_number if patient else None,
        creator_name=creator.full_name if creator else "Неизвестно"
    )


@router.put("/{case_id}", response_model=CaseSchema)
async def update_case(
        case_id: int,
        case_update: CaseUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Обновление информации о случае"""
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    # Проверка прав доступа
    if current_user.role not in [DoctorRole.ADMIN, DoctorRole.HEAD] and case.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к данному случаю")

    # Обновляем поля
    update_data = case_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    await db.commit()
    await db.refresh(case)

    return CaseSchema(
        id=case.id,
        patient_id=case.patient_id,
        creator_id=case.creator_id,
        admission_date=case.admission_date,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
        completed_at=case.completed_at,
        sent_to_webmis_at=case.sent_to_webmis_at
    )


@router.delete("/{case_id}")
async def delete_case(
        case_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head"))
):
    """Удаление случая (только для админа и заведующего)"""
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    await db.delete(case)
    await db.commit()

    return {"message": "Случай удален"}


@router.post("/{case_id}/complete")
async def complete_case(
        case_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Завершение случая"""
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    # Проверка прав доступа
    if current_user.role not in [DoctorRole.ADMIN, DoctorRole.HEAD] and case.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к данному случаю")

    case.status = CaseStatus.COMPLETED
    case.completed_at = datetime.utcnow()

    await db.commit()

    return {"message": "Случай завершен"}


@router.post("/{case_id}/send-to-webmis")
async def send_case_to_webmis(
        case_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head"))
):
    """Отправка случая в ВебМИС (только для админа и заведующего)"""
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    # Проверяем, что случай завершен
    if case.status != CaseStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Случай должен быть завершен перед отправкой в ВебМИС"
        )

    case.status = CaseStatus.SENT
    case.sent_to_webmis_at = datetime.utcnow()

    await db.commit()

    return {"message": "Случай отправлен в ВебМИС"}