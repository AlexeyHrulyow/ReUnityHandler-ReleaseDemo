from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from reunity_app.core.security import (
    verify_password,
    create_access_token,
    get_current_user,
    get_password_hash
)
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor
from reunity_app.schemas.auth import Token, LoginRequest, ChangePasswordRequest

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    """Аутентификация пользователя"""
    # Ищем пользователя по username
    result = await db.execute(
        select(Doctor).where(Doctor.username == form_data.username)
    )
    doctor = result.scalar_one_or_none()

    if not doctor or not verify_password(form_data.password, doctor.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь неактивен"
        )

    # Создаем токен
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": doctor.username},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/change-password")
async def change_password(
        request: ChangePasswordRequest,
        current_user: Doctor = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Смена пароля"""
    # Проверяем текущий пароль
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )

    # Обновляем пароль
    current_user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    return {"message": "Пароль успешно изменен"}


@router.get("/me")
async def read_current_user(
        current_user: Doctor = Depends(get_current_user)
):
    """Получение информации о текущем пользователе"""
    # Добавляем отладочную информацию
    print(f"DEBUG: Запрос от пользователя {current_user.username}")

    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
        "is_active": current_user.is_active
    }