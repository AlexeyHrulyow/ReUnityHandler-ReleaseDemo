from .auth import router as auth_router
from .patients import router as patients_router
from .cases import router as cases_router
from .doctors import router as doctors_router
from .documents import router as documents_router

__all__ = [
    "auth_router",
    "patients_router",
    "cases_router",
    "doctors_router",
    "documents_router"
]