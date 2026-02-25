from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path

# Определяем корневую директорию проекта
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # База данных - используем относительный путь к .env
    DATABASE_URL: str

    # Безопасность
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Настройки приложения
    APP_NAME: str = "ReUnityHandler"  # Изменено на ReUnityHandler
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://172.20.0.127:8000"
        "http://192.168.137.100:8000"
    ]

    # Интеграция с ВебМИС
    WEBMIS_BASE_URL: str = ""
    WEBMIS_LOGIN: str = ""
    WEBMIS_PASSWORD: str = ""

    class Config:
        # Указываем путь к .env файлу относительно корня проекта
        env_file = str(BASE_DIR / ".env")
        case_sensitive = True


settings = Settings()