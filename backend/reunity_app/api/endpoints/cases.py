from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_
from datetime import datetime, date

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Patient, Case as CaseModel, Document, CaseStatus, DocumentDoctorStatus
from reunity_app.schemas.case import CaseCreate, CaseUpdate, Case as CaseSchema, CaseWithPatient, DoctorStatusItem

router = APIRouter()


@router.post("/", response_model=CaseSchema)
async def create_case(
        case: CaseCreate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Создание нового случая"""
    result = await db.execute(select(Patient).where(Patient.id == case.patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Пациент не найден")

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

    # Создаём документ
    db_document = Document(
        case_id=db_case.id,
        content={}
    )
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)

    # Инициализируем содержимое документа
    db_document.initialize_content()
    await db.commit()

    # Создаём записи статусов для всех врачей, участвующих в процессе
    result_doctors = await db.execute(
        select(Doctor).where(Doctor.is_active == True, Doctor.show_in_status == True)
    )
    doctors = result_doctors.scalars().all()
    for doctor in doctors:
        status_record = DocumentDoctorStatus(
            document_id=db_document.id,
            doctor_id=doctor.id,
            completed=False
        )
        db.add(status_record)
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
        creator_id: Optional[int] = Query(None, description="Фильтр по создателю случая"),
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение списка случаев с фильтрацией"""
    query = select(CaseModel).join(Patient)

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

    if date_from:
        query = query.where(func.date(CaseModel.created_at) >= date_from)

    if date_to:
        query = query.where(func.date(CaseModel.created_at) <= date_to)

    if creator_id:
        query = query.where(CaseModel.creator_id == creator_id)

    query = query.offset(skip).limit(limit).order_by(CaseModel.created_at.desc())

    result = await db.execute(query)
    cases = result.scalars().all()

    cases_with_details = []
    for case in cases:
        patient_result = await db.execute(select(Patient).where(Patient.id == case.patient_id))
        patient = patient_result.scalar_one_or_none()

        creator_result = await db.execute(select(Doctor).where(Doctor.id == case.creator_id))
        creator = creator_result.scalar_one_or_none()

        document_result = await db.execute(select(Document).where(Document.case_id == case.id))
        document = document_result.scalar_one_or_none()

        # Получаем статусы врачей для этого документа
        doctors_status = []
        if document:
            status_q = select(
                Doctor,
                DocumentDoctorStatus.completed,
                DocumentDoctorStatus.filled_at
            ).join(
                DocumentDoctorStatus,
                and_(
                    DocumentDoctorStatus.doctor_id == Doctor.id,
                    DocumentDoctorStatus.document_id == document.id
                ),
                isouter=True
            ).where(
                Doctor.is_active == True,
                Doctor.show_in_status == True
            ).order_by(Doctor.status_order)

            status_result = await db.execute(status_q)
            for doctor, completed, filled_at in status_result:
                doctors_status.append(DoctorStatusItem(
                    doctor_id=doctor.id,
                    doctor_name=doctor.full_name,
                    doctor_role=doctor.role,
                    completed=completed if completed is not None else False,
                    filled_at=filled_at
                ))

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

        case_with_patient = CaseWithPatient(
            **case_data.dict(),
            patient_name=patient.full_name if patient else "Неизвестно",
            patient_insurance=patient.insurance_number if patient else None,
            patient_birth_date=patient.birth_date.date() if patient and patient.birth_date else None,
            creator_name=creator.full_name if creator else "Неизвестно",
            creator_role=creator.role if creator else None,
            doctors_status=doctors_status
        )

        cases_with_details.append(case_with_patient)

    return cases_with_details


@router.get("/{case_id}", response_model=CaseWithPatient)
async def get_case(
        case_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    document_result = await db.execute(select(Document).where(Document.case_id == case.id))
    document = document_result.scalar_one_or_none()

    patient_result = await db.execute(select(Patient).where(Patient.id == case.patient_id))
    patient = patient_result.scalar_one_or_none()

    creator_result = await db.execute(select(Doctor).where(Doctor.id == case.creator_id))
    creator = creator_result.scalar_one_or_none()

    doctors_status = []
    if document:
        status_q = select(
            Doctor,
            DocumentDoctorStatus.completed,
            DocumentDoctorStatus.filled_at
        ).join(
            DocumentDoctorStatus,
            and_(
                DocumentDoctorStatus.doctor_id == Doctor.id,
                DocumentDoctorStatus.document_id == document.id
            ),
            isouter=True
        ).where(
            Doctor.is_active == True,
            Doctor.show_in_status == True
        ).order_by(Doctor.status_order)

        status_result = await db.execute(status_q)
        for doctor, completed, filled_at in status_result:
            doctors_status.append(DoctorStatusItem(
                doctor_id=doctor.id,
                doctor_name=doctor.full_name,
                doctor_role=doctor.role,
                completed=completed if completed is not None else False,
                filled_at=filled_at
            ))

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
        creator_role=creator.role if creator else None,
        doctors_status=doctors_status
    )


@router.put("/{case_id}", response_model=CaseSchema)
async def update_case(
        case_id: int,
        case_update: CaseUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

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
        current_user: Doctor = Depends(get_current_active_user)
):
    """Удаление случая. Доступно администратору или создателю случая."""
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    if current_user.role != "admin" and case.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратор или создатель случая может удалить случай"
        )

    await db.delete(case)
    await db.commit()
    return {"message": "Случай удален"}


@router.post("/{case_id}/complete")
async def complete_case(
        case_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Завершение случая (только для создателя или администратора)"""
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    if current_user.role != "admin" and case.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только создатель случая или администратор может завершить случай"
        )

    case.status = CaseStatus.COMPLETED
    case.completed_at = datetime.utcnow()
    await db.commit()
    return {"message": "Случай завершен"}


@router.post("/{case_id}/uncomplete")
async def uncomplete_case(
        case_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Отмена завершения случая (только для создателя или администратора)"""
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    if current_user.role != "admin" and case.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только создатель случая или администратор может отменить завершение"
        )

    case.status = CaseStatus.IN_PROGRESS
    case.completed_at = None
    await db.commit()
    return {"message": "Завершение случая отменено"}


@router.post("/{case_id}/send-to-webmis")
async def send_case_to_webmis(
        case_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head"))
):
    result = await db.execute(select(CaseModel).where(CaseModel.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    if case.status != CaseStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Случай должен быть завершен перед отправкой в ВебМИС"
        )

    case.status = CaseStatus.SENT
    case.sent_to_webmis_at = datetime.utcnow()
    await db.commit()
    return {"message": "Случай отправлен в ВебМИС"}