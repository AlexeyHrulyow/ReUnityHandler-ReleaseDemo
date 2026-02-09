"""
Модуль безопасности и аутентификации
"""
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация
from reunity_app.core.config import settings
from reunity_app.db.session import get_db
from reunity_app.db.models import Doctor, DoctorRole

# Упрощенный контекст для хеширования паролей
pwd_context = CryptContext(
    schemes=["sha256_crypt"],
    deprecated="auto"
)

# Схема OAuth2 с указанием URL для получения токена
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True  # Автоматически вызывает 401 при отсутствии токена
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля с использованием SHA256

    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хеш пароля из базы данных

    Returns:
        bool: True если пароль верный
    """
    if not plain_password or not hashed_password:
        logger.warning("Пустой пароль или хеш")
        return False

    try:
        # Генерируем хеш из введенного пароля
        input_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        return input_hash == hashed_password
    except Exception as e:
        logger.error(f"Ошибка при проверке пароля: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля с использованием SHA256

    Args:
        password: Пароль для хеширования

    Returns:
        str: Хешированный пароль
    """
    if not password:
        raise ValueError("Пароль не может быть пустым")

    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена

    Args:
        data: Данные для кодирования в токен
        expires_delta: Время жизни токена

    Returns:
        str: Закодированный JWT токен
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        logger.debug(f"Токен создан, expires: {expire}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Ошибка создания токена: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания токена"
        )


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> Doctor:
    """
    Получение текущего пользователя по JWT токену

    Args:
        token: JWT токен из заголовка Authorization
        db: Сессия базы данных

    Returns:
        Doctor: Объект пользователя (врача)

    Raises:
        HTTPException: 401 если токен невалидный
    """
    logger.debug(f"Аутентификация пользователя, токен: {token[:20]}...")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Токен невалиден или истек",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Декодируем токен
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        username: str = payload.get("sub")
        if username is None:
            logger.warning("Токен не содержит username (sub)")
            raise credentials_exception

        logger.debug(f"Декодированный username: {username}")

    except JWTError as e:
        logger.error(f"Ошибка декодирования JWT: {e}")
        raise token_exception
    except Exception as e:
        logger.error(f"Неожиданная ошибка при декодировании токена: {e}")
        raise credentials_exception

    # Ищем пользователя в базе данных
    try:
        result = await db.execute(
            select(Doctor).where(Doctor.username == username)
        )
        user = result.scalar_one_or_none()

        if user is None:
            logger.warning(f"Пользователь {username} не найден в базе данных")
            raise credentials_exception

        logger.debug(f"Пользователь найден: {user.username}, роль: {user.role}, активен: {user.is_active}")
        return user

    except Exception as e:
        logger.error(f"Ошибка базы данных при поиске пользователя: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при проверке пользователя"
        )


async def get_current_active_user(
        current_user: Doctor = Depends(get_current_user)
) -> Doctor:
    """
    Проверка активности пользователя

    Args:
        current_user: Текущий пользователь из get_current_user

    Returns:
        Doctor: Активный пользователь

    Raises:
        HTTPException: 400 если пользователь неактивен
    """
    if not current_user.is_active:
        logger.warning(f"Попытка входа неактивного пользователя: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь неактивен"
        )

    return current_user


def require_role(*allowed_roles: str):
    """
    Декоратор для проверки ролей пользователя

    Args:
        *allowed_roles: Разрешенные роли

    Returns:
        Функция-декоратор для проверки роли
    """

    def role_checker(current_user: Doctor = Depends(get_current_active_user)):
        user_role = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role

        logger.debug(f"Проверка роли: пользователь {user_role}, разрешены {allowed_roles}")

        if user_role not in allowed_roles:
            logger.warning(
                f"Доступ запрещен: пользователь {current_user.username} "
                f"с ролью {user_role} пытается получить доступ к эндпоинту, "
                f"требующему роли {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции"
            )

        return current_user

    return role_checker


def can_edit_document_row(current_user: Doctor, row_name: str) -> bool:
    """
    Проверка прав на редактирование строки документа

    Args:
        current_user: Текущий пользователь
        row_name: Название строки документа

    Returns:
        bool: True если пользователь может редактировать строку
    """
    from reunity_app.db.models import NEUROLOGIST_ROWS, THERAPIST_ROWS

    user_role = current_user.role

    # Админ и заведующий могут редактировать все
    if user_role in [DoctorRole.ADMIN, DoctorRole.HEAD]:
        return True

    # Невролог может редактировать свои строки
    if user_role == DoctorRole.NEUROLOGIST and row_name in NEUROLOGIST_ROWS:
        return True

    # Терапевт может редактировать свои строки
    if user_role == DoctorRole.THERAPIST and row_name in THERAPIST_ROWS:
        return True

    return False


# Для обратной совместимости
get_current_user_sync = get_current_user
get_current_active_user_sync = get_current_active_user


async def validate_token(token: str) -> dict:
    """
    Валидация токена без доступа к базе данных

    Args:
        token: JWT токен

    Returns:
        dict: Декодированный payload

    Raises:
        HTTPException: Если токен невалиден
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"Ошибка валидации токена: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен невалиден или истек"
        )