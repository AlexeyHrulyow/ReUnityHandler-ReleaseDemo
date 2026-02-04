from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy import text
import os
from fastapi.templating import Jinja2Templates

# Импорты из нашего приложения
from reunity_app.core.config import settings
from reunity_app.db.base import Base
from reunity_app.db.session import engine

# ВАЖНО: Импортируем все модели явно
from reunity_app.db.models import (
    Patient, Doctor, Case, Document,
    DocumentSection, DocumentTemplate, WebmisFieldMapping
)

# Инициализация шаблонов
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)


async def create_tables():
    """Создание таблиц в базе данных"""
    try:
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)

            # Проверяем созданные таблицы
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
    lifespan=lifespan,
    redirect_slashes=False
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
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard")
async def dashboard_page(request: Request):
    """Панель управления"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/cases")
async def cases_page(request: Request):
    """Страница управления случаями"""
    return templates.TemplateResponse("cases.html", {"request": request})


@app.get("/patients")
async def patients_page(request: Request):
    """Страница управления пациентами"""
    return templates.TemplateResponse("patients.html", {"request": request})


@app.get("/document_edit")
async def document_edit_page(request: Request):
    """Страница редактирования документа"""
    return templates.TemplateResponse("document_edit.html", {"request": request})


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/health")
async def api_health_check():
    """Проверка здоровья приложения для API"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "api_version": "1.0.0"
    }


@app.get("/api/v1/tables")
async def list_tables():
    """Список всех таблиц в базе данных"""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        )
        tables = [row[0] for row in result.fetchall()]

    return {
        "tables": tables,
        "count": len(tables)
    }


@app.get("/api/v1/info")
async def api_info():
    """Информация об API"""
    return {
        "version": "1.0.0",
        "name": "ReUnityHandler API",
        "description": "API для системы совместного заполнения медицинских документов",
        "endpoints": {
            "auth": "/api/v1/auth",
            "patients": "/api/v1/patients",
            "cases": "/api/v1/cases",
            "doctors": "/api/v1/doctors",
            "documents": "/api/v1/documents"
        }
    }


# Импорты роутеров
from reunity_app.api.endpoints import auth, patients, cases, doctors, documents

# Подключаем роутеры
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Аутентификация"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Пациенты"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Случаи"])
app.include_router(doctors.router, prefix="/api/v1/doctors", tags=["Врачи"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Документы"])


# Тестовые endpoint для отладки
@app.get("/test-auth")
async def test_auth():
    """Тестовый endpoint для проверки аутентификации"""
    return {
        "message": "Это открытый endpoint, доступен без авторизации",
        "time": datetime.now().isoformat()
    }


@app.get("/test-protected")
async def test_protected(current_user: Doctor = Depends(auth.get_current_user)):
    """Тестовый защищенный endpoint"""
    return {
        "message": "Это защищенный endpoint",
        "user": current_user.username,
        "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    }


@app.post("/create-test-user")
async def create_test_user():
    """Создание тестового пользователя для отладки"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from reunity_app.db.session import get_db
    from reunity_app.db.models import Doctor, DoctorRole
    import hashlib

    async for db in get_db():
        # Проверяем, есть ли уже админ
        result = await db.execute(select(Doctor).where(Doctor.username == "admin"))
        existing = result.scalar_one_or_none()

        if existing:
            return {"message": "Пользователь уже существует", "username": "admin"}

        # Создаем нового админа
        hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
        doctor = Doctor(
            username="admin",
            hashed_password=hashed_password,
            last_name="Администратор",
            first_name="Системный",
            role=DoctorRole.ADMIN,
            is_active=True
        )
        db.add(doctor)
        await db.commit()
        await db.refresh(doctor)

        return {"message": "Пользователь создан", "username": "admin"}