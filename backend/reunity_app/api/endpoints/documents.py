from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Patient, Case, Document, DocumentSection, DocumentTemplate, WebmisFieldMapping
from reunity_app.schemas.document import (
    DocumentCreate, DocumentUpdate, Document as DocumentSchema,
    DocumentWithDetails, DocumentSectionCreate, DocumentSectionUpdate,
    DocumentSection as DocumentSectionSchema, DocumentSectionWithDetails
)

router = APIRouter()


@router.get("/", response_model=List[DocumentWithDetails])
async def list_documents(
        skip: int = 0,
        limit: int = 100,
        case_id: Optional[int] = Query(None, description="Фильтр по случаю"),
        doctor_id: Optional[int] = Query(None, description="Фильтр по врачу"),
        signed_only: bool = Query(False, description="Только подписанные"),
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение списка документов"""

    print(f"🔍 Запрос документов: case_id={case_id}, user={current_user.username}, role={current_user.role}")

    query = select(Document)

    # Применяем фильтры
    if case_id:
        query = query.where(Document.case_id == case_id)
        print(f"  Фильтр по case_id: {case_id}")

    if doctor_id:
        query = query.where(Document.signer_id == doctor_id)

    if signed_only:
        query = query.where(Document.signed_at.is_not(None))

    # Убрать фильтрацию по создателю - все врачи видят все документы
    # Врачи видят только документы своих случаев
    # if current_user.role not in ["admin", "head"]:
    #     # Получаем ID случаев, созданных текущим врачом
    #     subquery = select(Case.id).where(Case.creator_id == current_user.id)
    #     query = query.where(Document.case_id.in_(subquery))
    #     print(f"  Фильтр по создателю: текущий врач ID={current_user.id}")

    query = query.offset(skip).limit(limit).order_by(Document.created_at.desc())

    result = await db.execute(query)
    documents = result.scalars().all()

    print(f"  Найдено документов: {len(documents)}")

    # Формируем ответ с деталями
    documents_with_details = []
    for doc in documents:
        # Получаем информацию о случае
        case_result = await db.execute(
            select(Case).where(Case.id == doc.case_id)
        )
        case = case_result.scalar_one_or_none()

        # Получаем информацию о пациенте
        patient_info = None
        if case:
            patient_result = await db.execute(
                select(Patient).where(Patient.id == case.patient_id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient:
                patient_info = {
                    "id": patient.id,
                    "name": patient.full_name,
                    "insurance_number": patient.insurance_number
                }

        # Получаем информацию о подписавшем
        signer_name = None
        if doc.signer_id:
            doctor_result = await db.execute(
                select(Doctor).where(Doctor.id == doc.signer_id)
            )
            signer = doctor_result.scalar_one_or_none()
            if signer:
                signer_name = signer.full_name

        # Получаем информацию о шаблоне
        template_name = None
        if doc.template_id:
            template_result = await db.execute(
                select(DocumentTemplate).where(DocumentTemplate.id == doc.template_id)
            )
            template = template_result.scalar_one_or_none()
            if template:
                template_name = template.name

        doc_data = DocumentWithDetails(
            **doc.__dict__,
            case_info=patient_info,
            template_name=template_name,
            signer_name=signer_name
        )
        documents_with_details.append(doc_data)

    return documents_with_details


@router.post("/", response_model=DocumentSchema)
async def create_document(
        document: DocumentCreate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Создание нового документа"""
    # Проверяем, что случай существует
    case_result = await db.execute(
        select(Case).where(Case.id == document.case_id)
    )
    case = case_result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Случай не найден")

    # Проверяем права доступа
    if current_user.role not in ["admin", "head"] and case.creator_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Нет прав на создание документа для этого случая"
        )

    # Создаем документ
    db_document = Document(**document.dict())
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)

    return db_document


@router.get("/{document_id}", response_model=DocumentWithDetails)
async def get_document(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение документа по ID"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Получаем информацию о случае
    case_result = await db.execute(
        select(Case).where(Case.id == document.case_id)
    )
    case = case_result.scalar_one_or_none()

    # Проверяем права доступа
    # Убрать строгую проверку, чтобы все врачи могли видеть документы
    # if current_user.role not in ["admin", "head"]:
    #     if not case or case.creator_id != current_user.id:
    #         raise HTTPException(
    #             status_code=403,
    #             detail="Нет доступа к этому документу"
    #         )

    # Получаем детальную информацию
    patient_info = None
    if case:
        patient_result = await db.execute(
            select(Patient).where(Patient.id == case.patient_id)
        )
        patient = patient_result.scalar_one_or_none()
        if patient:
            patient_info = {
                "id": patient.id,
                "name": patient.full_name,
                "insurance_number": patient.insurance_number
            }

    # Получаем информацию о подписавшем
    signer_name = None
    if document.signer_id:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.id == document.signer_id)
        )
        signer = doctor_result.scalar_one_or_none()
        if signer:
            signer_name = signer.full_name

    # Получаем информацию о шаблоне
    template_name = None
    if document.template_id:
        template_result = await db.execute(
            select(DocumentTemplate).where(DocumentTemplate.id == document.template_id)
        )
        template = template_result.scalar_one_or_none()
        if template:
            template_name = template.name

    return DocumentWithDetails(
        **document.__dict__,
        case_info=patient_info,
        template_name=template_name,
        signer_name=signer_name
    )


@router.put("/{document_id}", response_model=DocumentSchema)
async def update_document(
        document_id: int,
        document_update: DocumentUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Обновление документа"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Получаем информацию о случае
    case_result = await db.execute(
        select(Case).where(Case.id == document.case_id)
    )
    case = case_result.scalar_one_or_none()

    # Проверяем права доступа
    if current_user.role not in ["admin", "head"]:
        if not case or case.creator_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Нет прав на редактирование этого документа"
            )

    # Нельзя редактировать подписанный документ
    if document.signed_at:
        raise HTTPException(
            status_code=400,
            detail="Нельзя редактировать подписанный документ"
        )

    # Обновляем поля
    update_data = document_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    await db.commit()
    await db.refresh(document)

    return document


@router.delete("/{document_id}")
async def delete_document(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head"))
):
    """Удаление документа (только для админа и заведующего)"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    await db.delete(document)
    await db.commit()

    return {"message": "Документ удален"}


@router.post("/{document_id}/sign")
async def sign_document(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Подписание документа"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    print(f"🔏 Попытка подписания документа {document_id}")
    print(
        f"   Статусы заполнения: Невролог={document.neurologist_completed}, Терапевт={document.therapist_completed}, Заведующий={document.head_completed}")

    # Проверяем, что все разделы заполнены
    if not document.neurologist_completed:
        raise HTTPException(
            status_code=400,
            detail="Раздел невролога не заполнен"
        )

    if not document.therapist_completed:
        raise HTTPException(
            status_code=400,
            detail="Раздел терапевта не заполнен"
        )

    if not document.head_completed:
        raise HTTPException(
            status_code=400,
            detail="Раздел заведующего не заполнен"
        )

    # Подписываем документ
    document.signer_id = current_user.id
    document.signed_at = datetime.utcnow()

    await db.commit()
    print(f"✅ Документ {document_id} подписан пользователем {current_user.username}")

    return {"message": "Документ подписан успешно"}


# Эндпоинты для разделов документов

@router.get("/{document_id}/sections", response_model=List[DocumentSectionWithDetails])
async def list_document_sections(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение разделов документа"""
    # Проверяем существование документа
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Проверяем права доступа
    case_result = await db.execute(
        select(Case).where(Case.id == document.case_id)
    )
    case = case_result.scalar_one_or_none()

    if current_user.role not in ["admin", "head"]:
        if not case or case.creator_id != current_user.id:
            # Проверяем, есть ли у врача разделы в этом документе
            sections_result = await db.execute(
                select(DocumentSection).where(
                    and_(
                        DocumentSection.document_id == document_id,
                        DocumentSection.doctor_id == current_user.id
                    )
                )
            )
            if not sections_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=403,
                    detail="Нет доступа к разделам этого документа"
                )

    # Получаем разделы
    result = await db.execute(
        select(DocumentSection)
        .where(DocumentSection.document_id == document_id)
        .order_by(DocumentSection.created_at.asc())
    )
    sections = result.scalars().all()

    # Формируем ответ с деталями
    sections_with_details = []
    for section in sections:
        # Получаем информацию о враче
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.id == section.doctor_id)
        )
        doctor = doctor_result.scalar_one_or_none()

        section_data = DocumentSectionWithDetails(
            **section.__dict__,
            doctor_name=doctor.full_name if doctor else None,
            document_info={"id": document.id, "case_id": document.case_id}
        )
        sections_with_details.append(section_data)

    return sections_with_details


@router.post("/{document_id}/sections", response_model=DocumentSectionSchema)
async def create_document_section(
        document_id: int,
        section: DocumentSectionCreate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head"))
):
    """Создание раздела документа (только для админа и заведующего)"""
    # Проверяем существование документа
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Проверяем, что документ не подписан
    if document.signed_at:
        raise HTTPException(
            status_code=400,
            detail="Нельзя добавлять разделы в подписанный документ"
        )

    # Проверяем, что врач существует
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.id == section.doctor_id)
    )
    doctor = doctor_result.scalar_one_or_none()

    if not doctor:
        raise HTTPException(status_code=404, detail="Врач не найден")

    # Проверяем уникальность названия раздела в документе
    existing_result = await db.execute(
        select(DocumentSection).where(
            and_(
                DocumentSection.document_id == document_id,
                DocumentSection.section_name == section.section_name
            )
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Раздел с названием '{section.section_name}' уже существует"
        )

    # Создаем раздел
    db_section = DocumentSection(**section.dict(), document_id=document_id)
    db.add(db_section)
    await db.commit()
    await db.refresh(db_section)

    return db_section


@router.get("/sections/{section_id}", response_model=DocumentSectionWithDetails)
async def get_document_section(
        section_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение раздела документа по ID"""
    result = await db.execute(
        select(DocumentSection).where(DocumentSection.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Раздел не найден")

    # Проверяем права доступа
    if current_user.role not in ["admin", "head"]:
        if section.doctor_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Нет доступа к этому разделу"
            )

    # Получаем информацию о враче
    doctor_result = await db.execute(
        select(Doctor).where(Doctor.id == section.doctor_id)
    )
    doctor = doctor_result.scalar_one_or_none()

    # Получаем информацию о документе
    doc_result = await db.execute(
        select(Document).where(Document.id == section.document_id)
    )
    document = doc_result.scalar_one_or_none()

    return DocumentSectionWithDetails(
        **section.__dict__,
        doctor_name=doctor.full_name if doctor else None,
        document_info={"id": document.id, "case_id": document.case_id} if document else None
    )


@router.put("/sections/{section_id}", response_model=DocumentSectionSchema)
async def update_document_section(
        section_id: int,
        section_update: DocumentSectionUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Обновление раздела документа"""
    result = await db.execute(
        select(DocumentSection).where(DocumentSection.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Раздел не найден")

    # Проверяем права доступа
    if current_user.role not in ["admin", "head"]:
        if section.doctor_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Нет прав на редактирование этого раздела"
            )

    # Проверяем, что раздел не подписан
    if section.is_signed and section_update.content:
        raise HTTPException(
            status_code=400,
            detail="Нельзя редактировать подписанный раздел"
        )

    # Обновляем поля
    update_data = section_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)

    # Если подписываем раздел
    if update_data.get("is_signed") and not section.is_signed:
        section.signed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(section)

    return section


@router.post("/sections/{section_id}/sign")
async def sign_document_section(
        section_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Подписание раздела документа"""
    result = await db.execute(
        select(DocumentSection).where(DocumentSection.id == section_id)
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(status_code=404, detail="Раздел не найден")

    # Проверяем права доступа
    if current_user.role not in ["admin", "head"]:
        if section.doctor_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Нет прав на подписание этого раздела"
            )

    # Проверяем, что раздел уже заполнен
    if not section.content or section.content == {}:
        raise HTTPException(
            status_code=400,
            detail="Нельзя подписать пустой раздел"
        )

    # Подписываем раздел
    section.is_signed = True
    section.signed_at = datetime.utcnow()

    await db.commit()

    return {"message": "Раздел подписан успешно"}


@router.get("/{document_id}/structure")
async def get_document_structure_redirect(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Редирект на document-table эндпоинт"""
    # Проверяем существование документа
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Возвращаем информацию для редиректа
    return {
        "message": "Используйте /api/v1/document-table/{document_id}/structure",
        "redirect_to": f"/api/v1/document-table/{document_id}/structure",
        "document_id": document_id,
        "case_id": document.case_id
    }