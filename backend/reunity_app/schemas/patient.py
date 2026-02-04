from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


class PatientBase(BaseModel):
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    insurance_number: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    insurance_number: Optional[str] = None


class Patient(PatientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True