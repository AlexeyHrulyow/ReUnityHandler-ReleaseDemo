from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
from enum import Enum


class DocumentRowEnum(str, Enum):
    HEADER = "header"
    PAIN_SYNDROME = "pain_syndrome"
    STATO_DYNAMIC = "stato_dynamic"
    MENTAL_FUNCTIONS = "mental_functions"
    INTERNAL_ORGANS = "internal_organs"
    SENSORY_FUNCTIONS = "sensory_functions"
    VITAL_ACTIVITY = "vital_activity"
    SELF_CARE = "self_care"
    MOBILITY = "mobility"
    WORK_ABILITY = "work_ability"
    COMMUNICATION = "communication"
    TOTAL_SCORE = "total_score"


class MainTableRow(BaseModel):
    id: str
    label: str
    is_section: bool = False
    values: Optional[List[str]] = None

    @validator('values', always=True)
    def validate_values(cls, v, values):
        if not values.get('is_section', False):
            if v is None or len(v) != 4:
                raise ValueError("Для обычной строки требуется ровно 4 значения")
        return v if v is not None else []


class MainTableRowUpdate(BaseModel):
    row_id: str
    values: List[str]

    @validator('values')
    def validate_values(cls, v):
        if len(v) != 4:
            raise ValueError("Для основной таблицы требуется 4 значения")
        return v


class ProcedureRow(BaseModel):
    id: str
    label: str
    values: List[str]

    @validator('values')
    def validate_values(cls, v):
        if len(v) != 2:
            raise ValueError("Для таблицы процедур требуется 2 значения")
        return v


class ProcedureRowUpdate(BaseModel):
    row_id: str
    values: List[str]

    @validator('values')
    def validate_values(cls, v):
        if len(v) != 2:
            raise ValueError("Для таблицы процедур требуется 2 значения")
        return v


class Goals(BaseModel):
    short_term: str
    long_term: str


class GoalsUpdate(BaseModel):
    short_term: Optional[str] = None
    long_term: Optional[str] = None


class HeaderFields(BaseModel):
    diagnosis_mkb: str
    rehab_potential: str
    rehab_prognosis: str


class HeaderFieldsUpdate(BaseModel):
    diagnosis_mkb: Optional[str] = None
    rehab_potential: Optional[str] = None
    rehab_prognosis: Optional[str] = None


class TableDates(BaseModel):
    admission: str
    intermediate: str
    discharge: str


class TableDatesUpdate(BaseModel):
    admission: Optional[str] = None
    intermediate: Optional[str] = None
    discharge: Optional[str] = None


class DocumentStructureResponse(BaseModel):
    header_fields: HeaderFields
    table_dates: TableDates
    main_table: List[MainTableRow]
    procedures_table: List[ProcedureRow]
    goals: Goals
    permissions: Dict[str, Any]
    completion_status: Dict[str, bool]  # ключи: reflexotherapist, physiotherapist, therapist_frm, neurologist_frm, psychologist