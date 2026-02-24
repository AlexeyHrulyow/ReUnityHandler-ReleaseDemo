from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from reunity_app.db.models import DoctorRole


class DoctorBase(BaseModel):
    username: str
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    role: DoctorRole = DoctorRole.THERAPIST


class DoctorCreate(DoctorBase):
    password: str


class DoctorUpdate(BaseModel):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    role: Optional[DoctorRole] = None
    is_active: Optional[bool] = None


class Doctor(DoctorBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ИЗМЕНЕНО: добавлена схема для запроса смены пароля администратором
class SetPasswordRequest(BaseModel):
    new_password: str