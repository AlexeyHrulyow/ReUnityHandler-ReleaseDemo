# reunity_app/schemas/case.py

from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List
from reunity_app.db.models import CaseStatus


class DoctorStatusItem(BaseModel):
    doctor_id: int
    doctor_name: str
    doctor_role: str
    completed: bool
    filled_at: Optional[datetime] = None


class CaseBase(BaseModel):
    patient_id: int
    admission_date: datetime
    status: CaseStatus = CaseStatus.DRAFT
    notes: Optional[str] = None


class CaseCreate(CaseBase):
    pass


class CaseUpdate(BaseModel):
    patient_id: Optional[int] = None
    admission_date: Optional[datetime] = None
    status: Optional[CaseStatus] = None
    completed_at: Optional[datetime] = None
    sent_to_webmis_at: Optional[datetime] = None
    notes: Optional[str] = None


class Case(CaseBase):
    id: int
    creator_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    sent_to_webmis_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CaseWithPatient(Case):
    patient_name: Optional[str] = None
    patient_insurance: Optional[str] = None
    patient_birth_date: Optional[date] = None
    creator_name: Optional[str] = None
    creator_role: Optional[str] = None
    doctors_status: List[DoctorStatusItem] = []   # заменяет отдельные поля