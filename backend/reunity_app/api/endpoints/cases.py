from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from datetime import datetime, date

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Patient, Case as CaseModel, Document, CaseStatus
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
        status=case.status,
        notes=case.notes
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

    return CaseSchema(
        id=db_case.id,
        patient_id=db_case.patient_id,
        creator_id=db_case.creator_id,
        admission_date=db_case.admission_date,
        status=db_case.status,
        notes=db_case.notes,
        created_at=db_case.created_at,
        updated_at=db_case.updated_at,
        completed_at=db_case.completed_at,
        sent_to_webmis_at=db_case.sent_to_webmis_at
    )


@router.get("/", response_model=List[CaseWithPatient])
async def list_cases(
        skip: int = 0,
        limit: int = 100,
        status: Optional[CaseStatus] = Query(None, description="Фильтр по статусу"),
        patient_id: Optional[int] = Query(None, description="Фильтр по пациенту"),
        search: Optional[str] = Query(None, description="Поиск по ФИО пациента"),
        date_from: Optional[date] = Query(None, description="Фильтр по дате с"),
        date_to: Optional[date] = Query(None, description="Фильтр по дате по"),
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

    # Фильтр по дате создания случая
    if date_from:
        query = query.where(func.date(CaseModel.created_at) >= date_from)

    if date_to:
        query = query.where(func.date(CaseModel.created_at) <= date_to)

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

        # Получаем информацию о документе
        document_result = await db.execute(
            select(Document).where(Document.case_id == case.id)
        )
        document = document_result.scalar_one_or_none()

        # Получаем информацию о разделах документа
        neurologist_completed = False
        therapist_completed = False
        head_completed = False

        if document:
            # Здесь позже добавим логику проверки статуса разделов
            pass

        # Создаем объект схемы
        case_data = CaseSchema(
            id=case.id,
            patient_id=case.patient_id,
            creator_id=case.creator_id,
            admission_date=case.admission_date,
            status=case.status,
            notes=case.notes,
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
            patient_birth_date=patient.birth_date.date() if patient and patient.birth_date else None,
            creator_name=creator.full_name if creator else "Неизвестно",
            neurologist_completed=neurologist_completed,
            therapist_completed=therapist_completed,
            head_completed=head_completed
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
        notes=case.notes,
        created_at=case.created_at,
        updated_at=case.updated_at,
        completed_at=case.completed_at,
        sent_to_webmis_at=case.sent_to_webmis_at
    )

    return CaseWithPatient(
        **case_data.dict(),
        patient_name=patient.full_name if patient else "Неизвестно",
        patient_insurance=patient.insurance_number if patient else None,
        patient_birth_date=patient.birth_date.date() if patient and patient.birth_date else None,
        creator_name=creator.full_name if creator else "Неизвестно",
        neurologist_completed=False,
        therapist_completed=False,
        head_completed=False
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
        notes=case.notes,
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