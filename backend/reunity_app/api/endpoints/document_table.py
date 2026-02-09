from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Document, DoctorRole, Case
from reunity_app.schemas.document_structure import DocumentRowUpdate, DocumentContent, DOCTOR_ROWS

router = APIRouter()


@router.get("/{document_id}/structure", response_model=Dict[str, Any])
async def get_document_structure(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение структуры документа с правами доступа"""
    # Получаем документ
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Проверяем права доступа
    case_result = await db.execute(
        select(Case).where(Case.id == document.case_id)
    )
    case = case_result.scalar_one_or_none()

    # Формируем структуру с правами доступа
    structure = {
        "table_data": document.content or {},
        "permissions": {
            "can_edit_all": current_user.role in [DoctorRole.ADMIN, DoctorRole.HEAD],
            "can_edit_neurologist": (
                    current_user.role == DoctorRole.NEUROLOGIST or
                    current_user.role in [DoctorRole.ADMIN, DoctorRole.HEAD]
            ),
            "can_edit_therapist": (
                    current_user.role == DoctorRole.THERAPIST or
                    current_user.role in [DoctorRole.ADMIN, DoctorRole.HEAD]
            ),
            "can_edit_head": current_user.role in [DoctorRole.HEAD, DoctorRole.ADMIN],
            "current_user_role": current_user.role.value
        },
        "doctor_rows": {
            "neurologist": DOCTOR_ROWS.neurologist_rows,
            "therapist": DOCTOR_ROWS.therapist_rows,
            "head": DOCTOR_ROWS.head_rows
        },
        "completion_status": {
            "neurologist": document.neurologist_completed,
            "therapist": document.therapist_completed,
            "head": document.head_completed
        }
    }

    return structure


@router.put("/{document_id}/row", response_model=Dict[str, Any])
async def update_document_row(
        document_id: int,
        row_update: DocumentRowUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Обновление строки документа"""
    # Получаем документ
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Проверяем, может ли пользователь редактировать эту строку
    can_edit = False

    # Админ и заведующий могут редактировать все
    if current_user.role in [DoctorRole.ADMIN, DoctorRole.HEAD]:
        can_edit = True
    # Невролог может редактировать свои строки
    elif current_user.role == DoctorRole.NEUROLOGIST:
        can_edit = row_update.row_name in DOCTOR_ROWS.neurologist_rows
    # Терапевт может редактировать свои строки
    elif current_user.role == DoctorRole.THERAPIST:
        can_edit = row_update.row_name in DOCTOR_ROWS.therapist_rows

    if not can_edit:
        raise HTTPException(
            status_code=403,
            detail=f"У вас нет прав для редактирования строки {row_update.row_name}"
        )

    # Обновляем строку
    document.update_row(row_update.row_name, row_update.values)

    # Обновляем статус заполнения
    await update_completion_status(document, row_update.row_name, current_user.role)

    # Пересчитываем итоговый балл
    document.calculate_total_score()

    await db.commit()
    await db.refresh(document)

    return {
        "message": "Строка обновлена",
        "row_name": row_update.row_name,
        "new_values": row_update.values
    }


async def update_completion_status(document: Document, row_name: str, user_role: DoctorRole):
    """Обновление статуса заполнения для врача"""
    now = datetime.utcnow()

    if user_role == DoctorRole.NEUROLOGIST and row_name in [r.value for r in DOCTOR_ROWS.neurologist_rows]:
        document.neurologist_filled_at = now
        # Проверяем, все ли строки невролога заполнены
        all_filled = all(
            document.content.get(row.value, ["", "", ""])[1] != "" and
            document.content.get(row.value, ["", "", ""])[2] != ""
            for row in DOCTOR_ROWS.neurologist_rows
        )
        document.neurologist_completed = all_filled

    elif user_role == DoctorRole.THERAPIST and row_name in [r.value for r in DOCTOR_ROWS.therapist_rows]:
        document.therapist_filled_at = now
        all_filled = all(
            document.content.get(row.value, ["", "", ""])[1] != "" and
            document.content.get(row.value, ["", "", ""])[2] != ""
            for row in DOCTOR_ROWS.therapist_rows
        )
        document.therapist_completed = all_filled

    elif user_role == DoctorRole.HEAD and row_name in [r.value for r in DOCTOR_ROWS.head_rows]:
        document.head_filled_at = now
        all_filled = all(
            document.content.get(row.value, ["", "", ""])[1] != "" and
            document.content.get(row.value, ["", "", ""])[2] != ""
            for row in DOCTOR_ROWS.head_rows
        )
        document.head_completed = all_filled


@router.post("/{document_id}/complete-section")
async def complete_section(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Отметить раздел как заполненный (для врачей)"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    now = datetime.utcnow()

    if current_user.role == DoctorRole.NEUROLOGIST:
        document.neurologist_completed = True
        document.neurologist_filled_at = now
    elif current_user.role == DoctorRole.THERAPIST:
        document.therapist_completed = True
        document.therapist_filled_at = now
    elif current_user.role == DoctorRole.HEAD:
        document.head_completed = True
        document.head_filled_at = now
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


@router.get("/{document_id}/completion-status")
async def get_completion_status(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """Получение статуса заполнения документа"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    return {
        "neurologist": {
            "completed": document.neurologist_completed,
            "filled_at": document.neurologist_filled_at.isoformat() if document.neurologist_filled_at else None
        },
        "therapist": {
            "completed": document.therapist_completed,
            "filled_at": document.therapist_filled_at.isoformat() if document.therapist_filled_at else None
        },
        "head": {
            "completed": document.head_completed,
            "filled_at": document.head_filled_at.isoformat() if document.head_filled_at else None
        },
        "all_completed": (
                document.neurologist_completed and
                document.therapist_completed and
                document.head_completed
        )
    }