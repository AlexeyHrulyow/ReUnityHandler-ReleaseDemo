"""
Главный файл приложения ReUnityHandler
"""
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from datetime import datetime
from sqlalchemy import text
import os
import logging

from sqlalchemy.ext.asyncio import AsyncSession

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты из нашего приложения
from reunity_app.core.config import settings
from reunity_app.db.base import Base
from reunity_app.db.session import engine, get_db
from reunity_app.db.models import (
    Patient, Doctor, Case, Document,
    DocumentSection, DocumentTemplate, WebmisFieldMapping
)
from reunity_app.core.security import get_current_user, get_current_active_user, oauth2_scheme

# Инициализация шаблонов
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)


async def create_tables():
    """Создание таблиц в базе данных"""
    try:
        logger.info("Создание таблиц в базе данных...")

        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)

            # Проверяем созданные таблицы
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]

            logger.info(f"✅ Таблицы базы данных созданы ({len(tables)} таблиц):")
            for table in sorted(tables):
                logger.info(f"  ✓ {table}")

            # Проверяем наличие пользователей
            doctor_count = await conn.execute(text("SELECT COUNT(*) FROM doctors"))
            doctor_count = doctor_count.scalar()

            if doctor_count == 0:
                logger.warning("⚠️  В базе данных нет пользователей. Используйте create_test_user.py для создания администратора")

    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        raise


async def check_database_connection():
    """Проверка подключения к базе данных"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("✅ Подключение к базе данных успешно")
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к базе данных: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    logger.info("🚀 Запуск ReUnityHandler...")

    # Проверяем подключение к базе данных
    if not await check_database_connection():
        logger.error("Не удалось подключиться к базе данных. Проверьте настройки в .env файле")
        logger.info(f"Используемый DATABASE_URL: {settings.DATABASE_URL}")

    # Создаем таблицы
    await create_tables()

    logger.info("✅ Приложение готово к работе")
    logger.info(f"📡 API доступно по адресу: http://localhost:8000")
    logger.info(f"📚 Документация: http://localhost:8000/docs")

    yield

    logger.info("🛑 Остановка приложения...")
    await engine.dispose()
    logger.info("✅ Соединения с базой данных закрыты")


# Создаем приложение FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Система управления медицинскими случаями отделения реабилитации",
    lifespan=lifespan,
    docs_url="/docs",  # Включаем документацию
    redoc_url="/redoc",  # Включаем альтернативную документацию
    openapi_url="/api/v1/openapi.json",
    redirect_slashes=False
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Импорты роутеров
from reunity_app.api.endpoints import auth, patients, cases, doctors, documents, document_table

# Подключаем роутеры
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Аутентификация"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Пациенты"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Случаи"])
app.include_router(doctors.router, prefix="/api/v1/doctors", tags=["Врачи"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Документы"])
app.include_router(document_table.router, prefix="/api/v1/document-table", tags=["Таблица документа"])


# ========== HTML СТРАНИЦЫ ==========

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


@app.get("/case_create")
async def case_create_page(request: Request):
    """Страница создания нового случая"""
    return templates.TemplateResponse("case_create.html", {"request": request})


@app.get("/document_table")
async def document_table_page(request: Request):
    """Страница редактирования таблицы документа"""
    return templates.TemplateResponse("document_table.html", {"request": request})


# ========== API ЭНДПОИНТЫ ==========

@app.get("/health")
async def health_check():
    """
    Проверка здоровья приложения (публичный)
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        db_status = "disconnected"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "app": settings.APP_NAME,
        "version": "1.0.0"
    }


@app.get("/api/v1/health")
async def api_health_check():
    """
    Проверка здоровья приложения для API (публичный)
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        db_status = "disconnected"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "api_version": "1.0.0",
        "app": settings.APP_NAME,
        "debug": settings.DEBUG
    }


@app.get("/api/v1/tables")
async def list_tables():
    """
    Список всех таблиц в базе данных (публичный)
    """
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
        )
        tables = [row[0] for row in result.fetchall()]

    return {
        "tables": tables,
        "count": len(tables),
        "database": "PostgreSQL"
    }


@app.get("/api/v1/info")
async def api_info():
    """
    Информация об API (публичный)
    """
    return {
        "version": "1.0.0",
        "name": "ReUnityHandler API",
        "description": "API для системы совместного заполнения медицинских документов",
        "endpoints": {
            "auth": "/api/v1/auth",
            "patients": "/api/v1/patients",
            "cases": "/api/v1/cases",
            "doctors": "/api/v1/doctors",
            "documents": "/api/v1/documents",
            "document-table": "/api/v1/document-table"
        },
        "authentication": "JWT Bearer Token",
        "documentation": "/docs"
    }


@app.get("/api/v1/routes")
async def list_routes():
    """
    Список всех доступных маршрутов (публичный)
    """
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = ", ".join(route.methods) if route.methods else "GET"
            routes.append({
                "path": route.path,
                "methods": methods,
                "name": route.name if hasattr(route, "name") else None
            })

    return {
        "routes": routes,
        "count": len(routes)
    }


@app.get("/api/v1/test-structure/{document_id}")
async def test_structure(
        document_id: int,
        db: AsyncSession = Depends(get_db)
):
    """Тестовый эндпоинт для проверки структуры"""
    from sqlalchemy import select

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        return {"error": "Документ не найден", "document_id": document_id}

    return {
        "document_id": document.id,
        "case_id": document.case_id,
        "content": document.content,
        "exists": True
    }


# ========== ОТЛАДОЧНЫЕ ЭНДПОИНТЫ ==========

@app.get("/api/v1/debug/auth-test")
async def debug_auth_test(current_user: Doctor = Depends(get_current_active_user)):
    """
    Тестовый эндпоинт для проверки авторизации (защищенный)
    """
    return {
        "status": "ok",
        "message": "Авторизация работает!",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
            "is_active": current_user.is_active
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/debug/public-test")
async def debug_public_test():
    """
    Публичный тестовый эндпоинт (публичный)
    """
    return {
        "status": "ok",
        "message": "Публичный эндпоинт работает",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/debug/db-check")
async def debug_db_check():
    """
    Проверка состояния базы данных (публичный)
    """
    try:
        async with engine.connect() as conn:
            # Проверяем основные таблицы
            tables_to_check = [
                "doctors", "patients", "cases", "documents",
                "document_sections", "document_templates"
            ]

            results = {}
            for table in tables_to_check:
                try:
                    result = await conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    )
                    count = result.scalar()
                    results[table] = {
                        "exists": True,
                        "count": count
                    }
                except Exception:
                    results[table] = {
                        "exists": False,
                        "count": 0
                    }

            return {
                "status": "ok",
                "database": "connected",
                "tables": results,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Ошибка проверки базы данных: {e}")
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/v1/debug/token-info")
async def debug_token_info(
    token: str = Depends(oauth2_scheme),
    current_user: Doctor = Depends(get_current_user)
):
    """
    Информация о текущем токене (защищенный)
    """
    from reunity_app.core.security import validate_token

    try:
        payload = validate_token(token)

        return {
            "status": "ok",
            "token_info": {
                "username": payload.get("sub"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "token_type": "Bearer"
            },
            "user_info": {
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role.value if hasattr(current_user.role, 'value') else current_user.role,
                "is_active": current_user.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка получения информации о токене: {str(e)}"
        )


# ========== ОБРАБОТЧИКИ ОШИБОК ==========

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    """
    Обработчик 404 ошибок
    """
    logger.warning(f"404 ошибка: {request.method} {request.url}")

    # Если запрос к API, возвращаем JSON
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Ресурс не найден",
                "path": request.url.path,
                "method": request.method
            }
        )

    # Иначе возвращаем HTML страницу
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "message": "Страница не найдена"},
        status_code=404
    )


@app.exception_handler(401)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    """
    Обработчик 401 ошибок
    """
    logger.warning(f"401 ошибка: {request.method} {request.url}")

    return JSONResponse(
        status_code=401,
        content={
            "detail": "Требуется авторизация",
            "path": request.url.path,
            "method": request.method
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


# Импорт для JSONResponse
from fastapi.responses import JSONResponse
from fastapi import status

# Импорт oauth2_scheme
from reunity_app.core.security import oauth2_scheme


# ========== ПРОМЕЖУТОЧНЫЕ ПРОВЕРКИ ==========

@app.on_event("startup")
async def startup_event():
    """
    Действия при запуске приложения
    """
    logger.info("=" * 50)
    logger.info(f"🚀 {settings.APP_NAME} запускается...")
    logger.info(f"📁 База данных: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    logger.info(f"🔧 Режим отладки: {settings.DEBUG}")
    logger.info(f"🌐 CORS origins: {settings.CORS_ORIGINS}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Действия при остановке приложения
    """
    logger.info("=" * 50)
    logger.info(f"🛑 {settings.APP_NAME} останавливается...")
    logger.info("=" * 50)


# ========== ДОПОЛНИТЕЛЬНЫЕ МАРШРУТЫ ==========

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Заглушка для favicon
    """
    return JSONResponse(content={}, status_code=204)


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    """
    Файл robots.txt
    """
    content = """User-agent: *
Disallow: /api/
Allow: /health
Allow: /api/v1/health
"""
    return Response(content=content, media_type="text/plain")


from fastapi.responses import Response