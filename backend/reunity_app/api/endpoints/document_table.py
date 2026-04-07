from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select, and_
from pydantic import BaseModel
from typing import Dict, List, Optional
from sqlalchemy.orm.attributes import flag_modified

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Document, DoctorRole, Case, DocumentDoctorStatus
from reunity_app.schemas.document_structure import (
    MainTableRowUpdate, ProcedureRowUpdate, GoalsUpdate,
    HeaderFieldsUpdate, TableDatesUpdate,
    DocumentStructureResponse, MainTableRow, ProcedureRow, Goals,
    HeaderFields, TableDates, AdditionalRow, AdditionalRowUpdate, AdditionalRowsUpdate,
    DoctorStatusItem  # добавим в schemas/document_structure.py
)

router = APIRouter()


async def get_document_or_404(document_id: int, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return document


async def get_or_create_doctor_status(
    document: Document,
    doctor_id: int,
    db: AsyncSession
) -> DocumentDoctorStatus:
    """Получить или создать запись статуса для врача в документе."""
    result = await db.execute(
        select(DocumentDoctorStatus).where(
            DocumentDoctorStatus.document_id == document.id,
            DocumentDoctorStatus.doctor_id == doctor_id
        )
    )
    status = result.scalar_one_or_none()
    if not status:
        status = DocumentDoctorStatus(
            document_id=document.id,
            doctor_id=doctor_id,
            completed=False
        )
        db.add(status)
        await db.flush()
    return status


@router.get("/{document_id}/structure", response_model=DocumentStructureResponse)
async def get_document_structure(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    print(f"Запрос структуры документа {document_id} от пользователя {current_user.username}")

    document = await get_document_or_404(document_id, db)

    if not document.content or "goals" not in document.content:
        print("Документ имеет старую структуру, инициализируем новой")
        document.initialize_content()
        if "additional_domains" not in document.content:
            document.initialize_additional_domains()
        await db.commit()
        await db.refresh(document)

    content = document.content

    header_fields = HeaderFields(
        diagnosis_mkb=content.get("diagnosis_mkb", ""),
        rehab_potential=content.get("rehab_potential", ""),
        rehab_prognosis=content.get("rehab_prognosis", "")
    )

    table_dates_data = content.get("table_dates", {"admission": "", "intermediate": "", "discharge": ""})
    table_dates = TableDates(
        admission=table_dates_data.get("admission", ""),
        intermediate=table_dates_data.get("intermediate", ""),
        discharge=table_dates_data.get("discharge", "")
    )

    main_table_rows = []
    for row in content.get("main_table", {}).get("rows", []):
        main_table_rows.append(
            MainTableRow(
                id=row.get("id", ""),
                label=row.get("label", ""),
                is_section=row.get("is_section", False),
                values=row.get("values", [])
            )
        )

    procedure_rows = []
    for row in content.get("procedures_table", {}).get("rows", []):
        procedure_rows.append(
            ProcedureRow(
                id=row.get("id", ""),
                label=row.get("label", ""),
                values=row.get("values", ["", ""])
            )
        )

    goals_data = content.get("goals", {"short_term": "", "long_term": ""})
    goals = Goals(
        short_term=goals_data.get("short_term", ""),
        long_term=goals_data.get("long_term", "")
    )

    permissions = {
        "can_edit_all": current_user.role == DoctorRole.ADMIN,
        "current_user_role": current_user.role
    }

    # Получаем статусы для всех врачей с show_in_status=true
    completion_status = []
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
        completion_status.append(
            DoctorStatusItem(
                doctor_id=doctor.id,
                doctor_name=doctor.full_name,
                doctor_role=doctor.role,
                completed=completed if completed is not None else False,
                filled_at=filled_at
            )
        )

    additional_rows = [
        AdditionalRow(**row) for row in document.content.get("additional_domains", [])
    ]

    return DocumentStructureResponse(
        header_fields=header_fields,
        table_dates=table_dates,
        main_table=main_table_rows,
        procedures_table=procedure_rows,
        goals=goals,
        permissions=permissions,
        additional_rows=additional_rows,
        completion_status=completion_status
    )


@router.put("/{document_id}/header-fields")
async def update_header_fields(
        document_id: int,
        fields_update: HeaderFieldsUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    print(f"Обновление полей верхней части")

    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")

    if fields_update.diagnosis_mkb is not None:
        document.content["diagnosis_mkb"] = fields_update.diagnosis_mkb
    if fields_update.rehab_potential is not None:
        document.content["rehab_potential"] = fields_update.rehab_potential
    if fields_update.rehab_prognosis is not None:
        document.content["rehab_prognosis"] = fields_update.rehab_prognosis

    flag_modified(document, "content")

    now = datetime.utcnow()
    # Обновляем дату заполнения для текущего врача, если он участвует в статусах
    doctor = await db.execute(select(Doctor).where(Doctor.id == current_user.id, Doctor.show_in_status == True))
    if doctor.scalar_one_or_none():
        status = await get_or_create_doctor_status(document, current_user.id, db)
        status.filled_at = now
        # не меняем completed автоматически, только дату

    await db.commit()
    return {"message": "Поля верхней части обновлены"}


@router.put("/{document_id}/table-dates")
async def update_table_dates(
        document_id: int,
        dates_update: TableDatesUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    print(f"Обновление дат таблицы")

    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")

    if "table_dates" not in document.content:
        document.content["table_dates"] = {"admission": "", "intermediate": "", "discharge": ""}

    if dates_update.admission is not None:
        document.content["table_dates"]["admission"] = dates_update.admission
    if dates_update.intermediate is not None:
        document.content["table_dates"]["intermediate"] = dates_update.intermediate
    if dates_update.discharge is not None:
        document.content["table_dates"]["discharge"] = dates_update.discharge

    flag_modified(document, "content")

    now = datetime.utcnow()
    doctor = await db.execute(select(Doctor).where(Doctor.id == current_user.id, Doctor.show_in_status == True))
    if doctor.scalar_one_or_none():
        status = await get_or_create_doctor_status(document, current_user.id, db)
        status.filled_at = now

    await db.commit()
    return {"message": "Даты таблицы обновлены"}


@router.put("/{document_id}/main-table-row")
async def update_main_table_row(
        document_id: int,
        row_update: MainTableRowUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    print(f"Обновление строки основной таблицы: {row_update.row_id}, значения: {row_update.values}")

    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")

    for row in document.content.get("main_table", {}).get("rows", []):
        if row["id"] == row_update.row_id and row.get("is_section", False):
            raise HTTPException(status_code=400, detail="Нельзя редактировать заголовок раздела")

    document.update_main_table_row(row_update.row_id, row_update.values)

    now = datetime.utcnow()
    doctor = await db.execute(select(Doctor).where(Doctor.id == current_user.id, Doctor.show_in_status == True))
    if doctor.scalar_one_or_none():
        status = await get_or_create_doctor_status(document, current_user.id, db)
        status.filled_at = now

    await db.commit()
    await db.refresh(document)

    return {
        "message": "Строка основной таблицы обновлена",
        "row_id": row_update.row_id,
        "new_values": row_update.values
    }


@router.put("/{document_id}/procedure-row")
async def update_procedure_row(
        document_id: int,
        row_update: ProcedureRowUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    print(f"Обновление строки процедур: {row_update.row_id}, значения: {row_update.values}")

    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")

    document.update_procedure_row(row_update.row_id, row_update.values)

    now = datetime.utcnow()
    doctor = await db.execute(select(Doctor).where(Doctor.id == current_user.id, Doctor.show_in_status == True))
    if doctor.scalar_one_or_none():
        status = await get_or_create_doctor_status(document, current_user.id, db)
        status.filled_at = now

    await db.commit()

    return {
        "message": "Строка таблицы процедур обновлена",
        "row_id": row_update.row_id,
        "new_values": row_update.values
    }


@router.put("/{document_id}/goals")
async def update_goals(
        document_id: int,
        goals_update: GoalsUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    print(f"Обновление целей: краткосрочная={goals_update.short_term}, долгосрочная={goals_update.long_term}")

    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")

    document.update_goals(short_term=goals_update.short_term, long_term=goals_update.long_term)

    now = datetime.utcnow()
    doctor = await db.execute(select(Doctor).where(Doctor.id == current_user.id, Doctor.show_in_status == True))
    if doctor.scalar_one_or_none():
        status = await get_or_create_doctor_status(document, current_user.id, db)
        status.filled_at = now

    await db.commit()

    return {"message": "Цели обновлены"}


class FullDocumentUpdate(BaseModel):
    diagnosis_mkb: str
    rehab_potential: str
    rehab_prognosis: str
    table_dates: Dict[str, str]
    main_table: Dict[str, List[str]]
    procedures_table: Dict[str, List[str]]
    goals: Dict[str, str]
    additional_rows: Optional[List[Dict[str, str]]] = None


@router.put("/{document_id}/full-content")
async def update_document_full(
        document_id: int,
        update_data: FullDocumentUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")

    if update_data.additional_rows is not None:
        document.content["additional_domains"] = update_data.additional_rows
        flag_modified(document, "content")

    document.content["diagnosis_mkb"] = update_data.diagnosis_mkb
    document.content["rehab_potential"] = update_data.rehab_potential
    document.content["rehab_prognosis"] = update_data.rehab_prognosis

    if "table_dates" not in document.content:
        document.content["table_dates"] = {}
    document.content["table_dates"]["admission"] = update_data.table_dates.get("admission", "")
    document.content["table_dates"]["intermediate"] = update_data.table_dates.get("intermediate", "")
    document.content["table_dates"]["discharge"] = update_data.table_dates.get("discharge", "")

    for row_id, values in update_data.main_table.items():
        for row in document.content.get("main_table", {}).get("rows", []):
            if row["id"] == row_id and row.get("is_section", False):
                continue
        document.update_main_table_row(row_id, values)

    for row_id, values in update_data.procedures_table.items():
        document.update_procedure_row(row_id, values)

    document.update_goals(
        short_term=update_data.goals.get("short_term", ""),
        long_term=update_data.goals.get("long_term", "")
    )

    now = datetime.utcnow()
    doctor = await db.execute(select(Doctor).where(Doctor.id == current_user.id, Doctor.show_in_status == True))
    if doctor.scalar_one_or_none():
        status = await get_or_create_doctor_status(document, current_user.id, db)
        status.filled_at = now

    await db.commit()

    return {"message": "Документ успешно обновлён"}


@router.post("/{document_id}/complete-section")
async def complete_section(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Отметить раздел как заполненный (для врачей)"""
    document = await get_document_or_404(document_id, db)
    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя завершить раздел в подписанном документе")

    # Проверяем, что текущий врач участвует в статусах
    doctor = await db.execute(
        select(Doctor).where(Doctor.id == current_user.id, Doctor.show_in_status == True)
    )
    if not doctor.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Ваш профиль не участвует в заполнении документа")

    status = await get_or_create_doctor_status(document, current_user.id, db)
    status.completed = True
    status.filled_at = datetime.utcnow()

    await db.commit()
    return {
        "message": f"Раздел отмечен как заполненный",
        "completed_at": status.filled_at.isoformat()
    }


@router.post("/{document_id}/uncomplete-my-section")
async def uncomplete_my_section(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Отмена завершения собственного раздела"""
    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя отменить завершение в подписанном документе")

    result = await db.execute(
        select(DocumentDoctorStatus).where(
            DocumentDoctorStatus.document_id == document.id,
            DocumentDoctorStatus.doctor_id == current_user.id
        )
    )
    status = result.scalar_one_or_none()
    if status:
        status.completed = False
        status.filled_at = None
        await db.commit()

    return {"message": "Завершение раздела отменено"}


@router.post("/{document_id}/uncomplete-section/{doctor_id}")
async def uncomplete_section_by_admin(
        document_id: int,
        doctor_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin"))
):
    """Отмена завершения раздела указанного врача (только для админа)"""
    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя отменить завершение в подписанном документе")

    result = await db.execute(
        select(DocumentDoctorStatus).where(
            DocumentDoctorStatus.document_id == document.id,
            DocumentDoctorStatus.doctor_id == doctor_id
        )
    )
    status = result.scalar_one_or_none()
    if status:
        status.completed = False
        status.filled_at = None
        await db.commit()

    return {"message": f"Завершение раздела врача отменено"}


@router.put("/{document_id}/additional-rows")
async def update_additional_rows(
    document_id: int,
    update: AdditionalRowsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Doctor = Depends(get_current_active_user)
):
    """Полная замена всех дополнительных строк."""
    document = await get_document_or_404(document_id, db)
    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")
    document.content["additional_domains"] = [row.dict() for row in update.rows]
    flag_modified(document, "content")
    document.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "Дополнительные строки обновлены"}


@router.post("/{document_id}/additional-rows")
async def add_additional_row(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Doctor = Depends(get_current_active_user)
):
    """Добавить новую пустую строку."""
    document = await get_document_or_404(document_id, db)
    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")
    document.add_additional_row()
    await db.commit()
    return {"message": "Строка добавлена"}


@router.delete("/{document_id}/additional-rows/{index}")
async def delete_additional_row(
    document_id: int,
    index: int,
    db: AsyncSession = Depends(get_db),
    current_user: Doctor = Depends(get_current_active_user)
):
    """Удалить строку по индексу."""
    document = await get_document_or_404(document_id, db)
    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")
    try:
        document.remove_additional_row(index)
    except IndexError:
        raise HTTPException(status_code=404, detail="Строка не найдена")
    await db.commit()
    return {"message": "Строка удалена"}


@router.put("/{document_id}/additional-row/{index}")
async def update_additional_row(
    document_id: int,
    index: int,
    row_update: AdditionalRowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Doctor = Depends(get_current_active_user)
):
    """Обновить одну строку по индексу."""
    document = await get_document_or_404(document_id, db)
    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя редактировать подписанный документ")
    document.update_additional_row(index, row_update.dict(exclude_unset=True))
    await db.commit()
    return {"message": "Строка обновлена"}


@router.get("/{document_id}/completion-status")
async def get_completion_status(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение статуса заполнения документа"""
    document = await get_document_or_404(document_id, db)

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

    result = await db.execute(status_q)
    statuses = []
    for doctor, completed, filled_at in result:
        statuses.append({
            "doctor_id": doctor.id,
            "doctor_name": doctor.full_name,
            "doctor_role": doctor.role,
            "completed": completed if completed is not None else False,
            "filled_at": filled_at.isoformat() if filled_at else None
        })
    all_completed = all(s["completed"] for s in statuses)
    return {"doctors_status": statuses, "all_completed": all_completed}