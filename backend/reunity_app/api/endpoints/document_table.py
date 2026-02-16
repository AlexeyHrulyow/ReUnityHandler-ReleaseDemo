from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select

from reunity_app.core.security import get_current_active_user, require_role
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, Document, DoctorRole, Case
from reunity_app.schemas.document_structure import DocumentRowUpdate, DocumentContent, DOCTOR_ROWS, DocumentRowEnum

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
    print(f"👤 Пользователь: {current_user.username}, роль: {current_user.role}")

    # Логируем полный запрос
    import json
    print(f"📄 Полный запрос: {json.dumps(row_update.dict(), indent=2)}")

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        print(f"❌ Документ {document_id} не найден")
        raise HTTPException(status_code=404, detail="Документ не найден")

    print(f"📄 Документ найден. ID: {document.id}, Case ID: {document.case_id}")
    print(f"📊 Текущий content: {json.dumps(document.content, indent=2, ensure_ascii=False)}")

    # Проверяем, может ли пользователь редактировать эту строку
    can_edit = False
    user_role = current_user.role

    print(f"🔍 Проверка прав для роли {user_role} на строку {row_update.row_name}")

    # Используем строки для сравнения, а не enum.value
    neurologist_rows = [r.value for r in DOCTOR_ROWS.neurologist_rows]
    therapist_rows = [r.value for r in DOCTOR_ROWS.therapist_rows]
    head_rows = [r.value for r in DOCTOR_ROWS.head_rows]

    print(f"📋 Невролог строки: {neurologist_rows}")
    print(f"📋 Терапевт строки: {therapist_rows}")
    print(f"📋 Заведующий строки: {head_rows}")

    # Админ может редактировать все
    if user_role == DoctorRole.ADMIN:
        can_edit = True
        print("✅ Админ может редактировать все")
    # Невролог может редактировать свои строки
    elif user_role == DoctorRole.NEUROLOGIST:
        can_edit = row_update.row_name in neurologist_rows
        print(f"🧠 Невролог может редактировать: {can_edit}")
    # Терапевт может редактировать свои строки
    elif user_role == DoctorRole.THERAPIST:
        can_edit = row_update.row_name in therapist_rows
        print(f"🩺 Терапевт может редактировать: {can_edit}")
    # Заведующий может редактировать только свои строки
    elif user_role == DoctorRole.HEAD:
        can_edit = row_update.row_name in head_rows
        print(f"👨‍⚕️ Заведующий может редактировать: {can_edit}")

    if not can_edit:
        print(
            f"❌ Отказано в доступе: {current_user.username} (роль: {user_role}) не может редактировать {row_update.row_name}")
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

    # Преобразуем строку в DocumentRow для обновления
    try:
        row_name_enum = DocumentRowEnum(row_update.row_name)
    except ValueError:
        print(f"⚠️ Предупреждение: '{row_update.row_name}' не соответствует DocumentRowEnum")
        # Используем строку напрямую, если enum не подходит
        row_name_enum = row_update.row_name

    # Обновляем строку с нормализованными значениями
    if isinstance(row_name_enum, DocumentRowEnum):
        document.update_row(row_name_enum, normalized_values)
    else:
        # Альтернативный метод для строк
        document.update_row_string(row_update.row_name, normalized_values)

    # Обновляем статус заполнения (но разрешаем пустые значения)
    await update_completion_status(document, row_update.row_name, user_role)

    # Пересчитываем итоговый балл (только если есть числа)
    document.calculate_total_score()

    await db.commit()
    await db.refresh(document)

    print(
        f"✅ Строка обновлена. Новый content для {row_update.row_name}: {document.content.get(row_update.row_name, [])}")
    print(f"📊 Полный content после обновления: {json.dumps(document.content, indent=2, ensure_ascii=False)}")

    return {
        "message": "Строка обновлена",
        "row_name": row_update.row_name,
        "new_values": normalized_values
    }


async def update_completion_status(document: Document, row_name: str, user_role: DoctorRole):
    """Обновление статуса заполнения для врача"""
    now = datetime.utcnow()

    print(f"🔄 Обновление статуса для врача: {user_role}, строка: {row_name}")

    # Используем строки для сравнения
    neurologist_rows = [r.value for r in DOCTOR_ROWS.neurologist_rows]
    therapist_rows = [r.value for r in DOCTOR_ROWS.therapist_rows]
    head_rows = [r.value for r in DOCTOR_ROWS.head_rows]

    if user_role == DoctorRole.NEUROLOGIST and row_name in neurologist_rows:
        document.neurologist_filled_at = now
        # Проверяем, что все строки невролога заполнены
        all_filled = all(
            document.content.get(row, ["", "", ""])[1] != "" or
            document.content.get(row, ["", "", ""])[2] != ""
            for row in neurologist_rows
        )
        document.neurologist_completed = all_filled
        print(f"   Невролог заполнен: {all_filled}")

    elif user_role == DoctorRole.THERAPIST and row_name in therapist_rows:
        document.therapist_filled_at = now
        all_filled = all(
            document.content.get(row, ["", "", ""])[1] != "" or
            document.content.get(row, ["", "", ""])[2] != ""
            for row in therapist_rows
        )
        document.therapist_completed = all_filled
        print(f"   Терапевт заполнен: {all_filled}")

    elif user_role == DoctorRole.HEAD and row_name in head_rows:
        document.head_filled_at = now
        # Для заведующего проверяем только header
        if row_name == DocumentRowEnum.HEADER.value:
            header_data = document.content.get(DocumentRowEnum.HEADER.value, ["", "", ""])
            document.head_completed = header_data[1] != "" and header_data[2] != ""
        print(f"   Заведующий заполнен: {document.head_completed}")


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

@router.post("/{document_id}/uncomplete-my-section")
async def uncomplete_my_section(
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(get_current_active_user)
):
    """
    Отмена завершения собственного раздела.
    Доступно для врачей (невролог, терапевт) и заведующего.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя отменить завершение подписанного документа")

    # Определяем, какой раздел сбрасывать в зависимости от роли
    role = current_user.role
    if role == DoctorRole.NEUROLOGIST:
        document.neurologist_completed = False
        document.neurologist_filled_at = None
    elif role == DoctorRole.THERAPIST:
        document.therapist_completed = False
        document.therapist_filled_at = None
    elif role == DoctorRole.HEAD:
        document.head_completed = False
        document.head_filled_at = None
    else:
        raise HTTPException(
            status_code=403,
            detail="Только невролог, терапевт или заведующий могут отменить свой раздел"
        )

    await db.commit()
    return {"message": f"Завершение раздела '{role.value}' отменено"}


@router.post("/{document_id}/uncomplete-section/{target_role}")
async def uncomplete_section_by_admin(
        document_id: int,
        target_role: str,
        db: AsyncSession = Depends(get_db),
        current_user: Doctor = Depends(require_role("admin", "head"))
):
    """
    Отмена завершения раздела указанной роли.
    Только для администратора и заведующего.
    target_role: neurologist, therapist, head
    """
    # Проверяем допустимость целевой роли
    if target_role not in ["neurologist", "therapist", "head"]:
        raise HTTPException(status_code=400, detail="Недопустимая целевая роль")

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if document.signed_at:
        raise HTTPException(status_code=400, detail="Нельзя отменить завершение подписанного документа")

    # Сбрасываем соответствующий раздел
    if target_role == "neurologist":
        document.neurologist_completed = False
        document.neurologist_filled_at = None
    elif target_role == "therapist":
        document.therapist_completed = False
        document.therapist_filled_at = None
    elif target_role == "head":
        document.head_completed = False
        document.head_filled_at = None

    await db.commit()
    return {"message": f"Завершение раздела '{target_role}' отменено администратором"}

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