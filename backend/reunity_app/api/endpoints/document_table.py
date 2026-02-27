from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, List, Optional

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Document, DoctorRole, Case
from reunity_app.schemas.document_structure import (
    MainTableRowUpdate, ProcedureRowUpdate, GoalsUpdate,
    HeaderFieldsUpdate, TableDatesUpdate,
    DocumentStructureResponse, MainTableRow, ProcedureRow, Goals,
    HeaderFields, TableDates
)

router = APIRouter()


async def get_document_or_404(document_id: int, db: AsyncSession) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return document


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
        "current_user_role": current_user.role.value
    }

    completion_status = {
        "reflexotherapist": document.reflexotherapist_completed,
        "physiotherapist": document.physiotherapist_completed,
        "therapist_frm": document.therapist_frm_completed,
        "neurologist_frm": document.neurologist_frm_completed,
        "psychologist": document.psychologist_completed
    }

    return DocumentStructureResponse(
        header_fields=header_fields,
        table_dates=table_dates,
        main_table=main_table_rows,
        procedures_table=procedure_rows,
        goals=goals,
        permissions=permissions,
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

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(document, "content")

    now = datetime.utcnow()
    # Обновляем даты заполнения для соответствующих ролей
    if current_user.role == DoctorRole.REFLEXOTHERAPIST:
        document.reflexotherapist_filled_at = now
    elif current_user.role == DoctorRole.PHYSIOTHERAPIST:
        document.physiotherapist_filled_at = now
    elif current_user.role == DoctorRole.THERAPIST_FRM:
        document.therapist_frm_filled_at = now
    elif current_user.role == DoctorRole.NEUROLOGIST_FRM:
        document.neurologist_frm_filled_at = now
    elif current_user.role == DoctorRole.PSYCHOLOGIST:
        document.psychologist_filled_at = now

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

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(document, "content")

    now = datetime.utcnow()
    if current_user.role == DoctorRole.REFLEXOTHERAPIST:
        document.reflexotherapist_filled_at = now
    elif current_user.role == DoctorRole.PHYSIOTHERAPIST:
        document.physiotherapist_filled_at = now
    elif current_user.role == DoctorRole.THERAPIST_FRM:
        document.therapist_frm_filled_at = now
    elif current_user.role == DoctorRole.NEUROLOGIST_FRM:
        document.neurologist_frm_filled_at = now
    elif current_user.role == DoctorRole.PSYCHOLOGIST:
        document.psychologist_filled_at = now

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
    if current_user.role == DoctorRole.REFLEXOTHERAPIST:
        document.reflexotherapist_filled_at = now
    elif current_user.role == DoctorRole.PHYSIOTHERAPIST:
        document.physiotherapist_filled_at = now
    elif current_user.role == DoctorRole.THERAPIST_FRM:
        document.therapist_frm_filled_at = now
    elif current_user.role == DoctorRole.NEUROLOGIST_FRM:
        document.neurologist_frm_filled_at = now
    elif current_user.role == DoctorRole.PSYCHOLOGIST:
        document.psychologist_filled_at = now

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
    if current_user.role == DoctorRole.REFLEXOTHERAPIST:
        document.reflexotherapist_filled_at = now
    elif current_user.role == DoctorRole.PHYSIOTHERAPIST:
        document.physiotherapist_filled_at = now
    elif current_user.role == DoctorRole.THERAPIST_FRM:
        document.therapist_frm_filled_at = now
    elif current_user.role == DoctorRole.NEUROLOGIST_FRM:
        document.neurologist_frm_filled_at = now
    elif current_user.role == DoctorRole.PSYCHOLOGIST:
        document.psychologist_filled_at = now

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
    if current_user.role == DoctorRole.REFLEXOTHERAPIST:
        document.reflexotherapist_filled_at = now
    elif current_user.role == DoctorRole.PHYSIOTHERAPIST:
        document.physiotherapist_filled_at = now
    elif current_user.role == DoctorRole.THERAPIST_FRM:
        document.therapist_frm_filled_at = now
    elif current_user.role == DoctorRole.NEUROLOGIST_FRM:
        document.neurologist_frm_filled_at = now
    elif current_user.role == DoctorRole.PSYCHOLOGIST:
        document.psychologist_filled_at = now

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
    if current_user.role == DoctorRole.REFLEXOTHERAPIST:
        document.reflexotherapist_filled_at = now
    elif current_user.role == DoctorRole.PHYSIOTHERAPIST:
        document.physiotherapist_filled_at = now
    elif current_user.role == DoctorRole.THERAPIST_FRM:
        document.therapist_frm_filled_at = now
    elif current_user.role == DoctorRole.NEUROLOGIST_FRM:
        document.neurologist_frm_filled_at = now
    elif current_user.role == DoctorRole.PSYCHOLOGIST:
        document.psychologist_filled_at = now

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
    now = datetime.utcnow()

    if current_user.role == DoctorRole.REFLEXOTHERAPIST:
        document.reflexotherapist_completed = True
        document.reflexotherapist_filled_at = now
    elif current_user.role == DoctorRole.PHYSIOTHERAPIST:
        document.physiotherapist_completed = True
        document.physiotherapist_filled_at = now
    elif current_user.role == DoctorRole.THERAPIST_FRM:
        document.therapist_frm_completed = True
        document.therapist_frm_filled_at = now
    elif current_user.role == DoctorRole.NEUROLOGIST_FRM:
        document.neurologist_frm_completed = True
        document.neurologist_frm_filled_at = now
    elif current_user.role == DoctorRole.PSYCHOLOGIST:
        document.psychologist_completed = True
        document.psychologist_filled_at = now
    else:
        raise HTTPException(
            status_code=400,
            detail="Только врачи могут отмечать разделы как заполненные"
        )

    await db.commit()
    return {
        "message": f"Раздел {current_user.role.value} отмечен как заполненный",
        "completed_at": now.isoformat()
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
        raise HTTPException(status_code=400, detail="Нельзя отменить завершение подписанного документа")

    role = current_user.role
    if role == DoctorRole.REFLEXOTHERAPIST:
        document.reflexotherapist_completed = False
        document.reflexotherapist_filled_at = None
    elif role == DoctorRole.PHYSIOTHERAPIST:
        document.physiotherapist_completed = False
        document.physiotherapist_filled_at = None
    elif role == DoctorRole.THERAPIST_FRM:
        document.therapist_frm_completed = False
        document.therapist_frm_filled_at = None
    elif role == DoctorRole.NEUROLOGIST_FRM:
        document.neurologist_frm_completed = False
        document.neurologist_frm_filled_at = None
    elif role == DoctorRole.PSYCHOLOGIST:
        document.psychologist_completed = False
        document.psychologist_filled_at = None
    else:
        raise HTTPException(
            status_code=403,
            detail="Только врач может отменить свой раздел"
        )

    await db.commit()
    return {"message": f"Завершение раздела '{role.value}' отменено"}


@router.post("/{document_id}/uncomplete-section/{target_role}")
async def uncomplete_section_by_admin(
        document_id: int,
        target_role: str,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin"))
):
    """Отмена завершения раздела указанной роли (только для админа)"""
    allowed_roles = ["reflexotherapist", "physiotherapist", "therapist_frm", "neurologist_frm", "psychologist"]
    if target_role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Недопустимая целевая роль")

    document = await get_document_or_404(document_id, db)

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя отменить завершение подписанного документа")

    if target_role == "reflexotherapist":
        document.reflexotherapist_completed = False
        document.reflexotherapist_filled_at = None
    elif target_role == "physiotherapist":
        document.physiotherapist_completed = False
        document.physiotherapist_filled_at = None
    elif target_role == "therapist_frm":
        document.therapist_frm_completed = False
        document.therapist_frm_filled_at = None
    elif target_role == "neurologist_frm":
        document.neurologist_frm_completed = False
        document.neurologist_frm_filled_at = None
    elif target_role == "psychologist":
        document.psychologist_completed = False
        document.psychologist_filled_at = None

    await db.commit()
    return {"message": f"Завершение раздела '{target_role}' отменено администратором"}


@router.get("/{document_id}/completion-status")
async def get_completion_status(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение статуса заполнения документа"""
    document = await get_document_or_404(document_id, db)

    return {
        "reflexotherapist": {
            "completed": document.reflexotherapist_completed,
            "filled_at": document.reflexotherapist_filled_at.isoformat() if document.reflexotherapist_filled_at else None
        },
        "physiotherapist": {
            "completed": document.physiotherapist_completed,
            "filled_at": document.physiotherapist_filled_at.isoformat() if document.physiotherapist_filled_at else None
        },
        "therapist_frm": {
            "completed": document.therapist_frm_completed,
            "filled_at": document.therapist_frm_filled_at.isoformat() if document.therapist_frm_filled_at else None
        },
        "neurologist_frm": {
            "completed": document.neurologist_frm_completed,
            "filled_at": document.neurologist_frm_filled_at.isoformat() if document.neurologist_frm_filled_at else None
        },
        "psychologist": {
            "completed": document.psychologist_completed,
            "filled_at": document.psychologist_filled_at.isoformat() if document.psychologist_filled_at else None
        },
        "all_completed": (
            document.reflexotherapist_completed and
            document.physiotherapist_completed and
            document.therapist_frm_completed and
            document.neurologist_frm_completed and
            document.psychologist_completed
        )
    }