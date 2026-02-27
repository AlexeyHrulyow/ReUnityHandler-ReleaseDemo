from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List
from reunity_app.db.models import CaseStatus


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

    # Новые поля для статусов врачей
    reflexotherapist_completed: bool = False
    physiotherapist_completed: bool = False
    therapist_frm_completed: bool = False
    neurologist_frm_completed: bool = False
    psychologist_completed: bool = False