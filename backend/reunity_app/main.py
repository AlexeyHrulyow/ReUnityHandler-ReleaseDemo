from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy import text  # <-- ДОБАВИТЬ ЭТО

# Импорты из нашего приложения
from reunity_app.core.config import settings
from reunity_app.db.base import Base
from reunity_app.db.session import engine

# ВАЖНО: Импортируем все модели явно
from reunity_app.db.models import (
    Patient, Doctor, Case, Document,
    DocumentSection, DocumentTemplate, WebmisFieldMapping
)


async def create_tables():
    """Создание таблиц в базе данных"""
    try:
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)

            # Проверяем созданные таблицы
            # ИСПРАВЛЕНО: Используем text() для сырого SQL
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]

            print("✅ Таблицы базы данных созданы:")
            for table in sorted(tables):
                print(f"  ✓ {table}")

    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    print("🚀 Запуск ReUnityHandler...")
    await create_tables()
    print("✅ Приложение готово к работе")

    yield

    print("🛑 Остановка приложения...")
    await engine.dispose()
    print("✅ Соединения закрыты")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Система управления медицинскими случаями отделения реабилитации",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Добро пожаловать в ReUnityHandler!",
        "version": "1.0.0",
        "status": "работает",
        "docs": "/docs",
        "api": "/api/v1"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    try:
        async with engine.connect() as conn:
            # ИСПРАВЛЕНО: Используем text() для сырого SQL
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/tables")
async def list_tables():
    """Список всех таблиц в базе данных"""
    async with engine.connect() as conn:
        # ИСПРАВЛЕНО: Используем text() для сырого SQL
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        )
        tables = [row[0] for row in result.fetchall()]

    return {
        "tables": tables,
        "count": len(tables)
    }