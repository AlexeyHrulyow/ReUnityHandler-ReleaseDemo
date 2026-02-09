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

    # Формируем структуру с правами доступа
    structure = {
        "table_data": document.content or {},
        "permissions": {
            "can_edit_all": current_user.role == DoctorRole.ADMIN,  # Только админ может редактировать все
            "can_edit_neurologist": current_user.role == DoctorRole.NEUROLOGIST,
            "can_edit_therapist": current_user.role == DoctorRole.THERAPIST,
            "can_edit_head": current_user.role == DoctorRole.HEAD,
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
    print(f"📥 Получен запрос на обновление строки: {row_update.row_name}, значения: {row_update.values}")

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        print(f"❌ Документ {document_id} не найден")
        raise HTTPException(status_code=404, detail="Документ не найден")

    print(f"📄 Документ найден. Текущий content: {document.content.get(row_update.row_name.value)}")

    # Проверяем, может ли пользователь редактировать эту строку
    can_edit = False

    # Админ может редактировать все
    if current_user.role == DoctorRole.ADMIN:
        can_edit = True
    # Невролог может редактировать свои строки
    elif current_user.role == DoctorRole.NEUROLOGIST:
        can_edit = row_update.row_name in [r.value for r in DOCTOR_ROWS.neurologist_rows]
    # Терапевт может редактировать свои строки
    elif current_user.role == DoctorRole.THERAPIST:
        can_edit = row_update.row_name in [r.value for r in DOCTOR_ROWS.therapist_rows]
    # Заведующий может редактировать только свои строки
    elif current_user.role == DoctorRole.HEAD:
        can_edit = row_update.row_name in [r.value for r in DOCTOR_ROWS.head_rows]

    if not can_edit:
        raise HTTPException(
            status_code=403,
            detail=f"У вас нет прав для редактирования строки {row_update.row_name}"
        )

    # Проверяем и нормализуем значения (разрешаем пустые строки)
    normalized_values = []
    for value in row_update.values:
        if value is None:
            normalized_values.append("")
        else:
            # Преобразуем в строку и обрезаем пробелы
            normalized_values.append(str(value).strip())

    print(f"🔧 Нормализованные значения: {normalized_values}")

    # Обновляем строку с нормализованными значениями
    document.update_row(row_update.row_name, normalized_values)

    # Обновляем статус заполнения (но разрешаем пустые значения)
    await update_completion_status(document, row_update.row_name, current_user.role)

    # Пересчитываем итоговый балл (только если есть числа)
    document.calculate_total_score()

    await db.commit()
    await db.refresh(document)

    print(f"✅ Строка обновлена. Новый content: {document.content.get(row_update.row_name.value)}")

    return {
        "message": "Строка обновлена",
        "row_name": row_update.row_name.value,
        "new_values": normalized_values
    }


async def update_completion_status(document: Document, row_name: str, user_role: DoctorRole):
    """Обновление статуса заполнения для врача"""
    now = datetime.utcnow()

    print(f"🔄 Обновление статуса для врача: {user_role}, строка: {row_name}")

    if user_role == DoctorRole.NEUROLOGIST and row_name in [r.value for r in DOCTOR_ROWS.neurologist_rows]:
        document.neurologist_filled_at = now
        # ПРАВИЛЬНАЯ ПРОВЕРКА: строка считается заполненной если есть хотя бы одно значение
        all_filled = all(
            document.content.get(row.value, ["", "", ""])[1] != "" or
            document.content.get(row.value, ["", "", ""])[2] != ""
            for row in DOCTOR_ROWS.neurologist_rows
        )
        document.neurologist_completed = all_filled
        print(f"   Невролог заполнен: {all_filled}")
        print(
            f"   Данные: { {row.value: document.content.get(row.value, ['', '', '']) for row in DOCTOR_ROWS.neurologist_rows} }")


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