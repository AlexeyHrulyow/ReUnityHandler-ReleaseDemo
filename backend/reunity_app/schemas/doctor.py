from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from reunity_app.db.models import DoctorRole
from pydantic import BaseModel
from typing import List

class DoctorStatusUpdate(BaseModel):
    id: int
    show_in_status: bool
    status_order: int

class DoctorStatusSettingsBatch(BaseModel):
    settings: List[DoctorStatusUpdate]

class DoctorBase(BaseModel):
    username: str
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    role: DoctorRole = DoctorRole.THERAPIST_FRM  # ← должно быть THERAPIST_FRM
    show_in_status: bool = False
    status_order: int = 0


class DoctorCreate(DoctorBase):
    password: str


class DoctorUpdate(BaseModel):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    role: Optional[DoctorRole] = None
    is_active: Optional[bool] = None
    username: Optional[str] = None  # добавлено


class Doctor(DoctorBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SetPasswordRequest(BaseModel):
    new_password: str