from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
from enum import Enum

# Для обратной совместимости (можно оставить, если где-то используются)
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


# Новая схема для строки основной таблицы с поддержкой заголовков разделов
class MainTableRow(BaseModel):
    id: str
    label: str
    is_section: bool = False
    values: Optional[List[str]] = None  # Для заголовков sections values = None или пустой список

    @validator('values', always=True)
    def validate_values(cls, v, values):
        if not values.get('is_section', False):
            if v is None or len(v) != 4:
                raise ValueError("Для обычной строки требуется ровно 4 значения")
        return v if v is not None else []


# Схема для обновления строки основной таблицы (только для обычных строк)
class MainTableRowUpdate(BaseModel):
    row_id: str
    values: List[str]

    @validator('values')
    def validate_values(cls, v):
        if len(v) != 4:
            raise ValueError("Для основной таблицы требуется 4 значения")
        return v


# Схема для строки таблицы процедур
class ProcedureRow(BaseModel):
    id: str
    label: str
    values: List[str]  # 2 элемента: [количество, примечание]

    @validator('values')
    def validate_values(cls, v):
        if len(v) != 2:
            raise ValueError("Для таблицы процедур требуется 2 значения")
        return v


# Схема для обновления строки таблицы процедур
class ProcedureRowUpdate(BaseModel):
    row_id: str
    values: List[str]

    @validator('values')
    def validate_values(cls, v):
        if len(v) != 2:
            raise ValueError("Для таблицы процедур требуется 2 значения")
        return v


# Целевой блок (два поля)
class Goals(BaseModel):
    short_term: str
    long_term: str


class GoalsUpdate(BaseModel):
    short_term: Optional[str] = None
    long_term: Optional[str] = None


# Поля верхней части документа (clinical_diagnosis_mkb удалено)
class HeaderFields(BaseModel):
    diagnosis_mkb: str
    rehab_potential: str
    rehab_prognosis: str


class HeaderFieldsUpdate(BaseModel):
    diagnosis_mkb: Optional[str] = None
    rehab_potential: Optional[str] = None
    rehab_prognosis: Optional[str] = None


# Даты в шапке таблицы
class TableDates(BaseModel):
    admission: str
    intermediate: str
    discharge: str


class TableDatesUpdate(BaseModel):
    admission: Optional[str] = None
    intermediate: Optional[str] = None
    discharge: Optional[str] = None


# Полная структура документа для ответа (other_fields удалено)
class DocumentStructureResponse(BaseModel):
    header_fields: HeaderFields
    table_dates: TableDates
    main_table: List[MainTableRow]
    procedures_table: List[ProcedureRow]
    goals: Goals
    permissions: Dict[str, Any]
    completion_status: Dict[str, bool]


# Для совместимости со старыми эндпоинтами, если они ещё используются
class DoctorRows(BaseModel):
    neurologist_rows: List[DocumentRowEnum]
    therapist_rows: List[DocumentRowEnum]
    head_rows: List[DocumentRowEnum]


DOCTOR_ROWS = DoctorRows(
    neurologist_rows=[
        DocumentRowEnum.PAIN_SYNDROME,
        DocumentRowEnum.STATO_DYNAMIC,
        DocumentRowEnum.MENTAL_FUNCTIONS,
        DocumentRowEnum.INTERNAL_ORGANS,
        DocumentRowEnum.SENSORY_FUNCTIONS
    ],
    therapist_rows=[
        DocumentRowEnum.VITAL_ACTIVITY,
        DocumentRowEnum.SELF_CARE,
        DocumentRowEnum.MOBILITY,
        DocumentRowEnum.WORK_ABILITY,
        DocumentRowEnum.COMMUNICATION
    ],
    head_rows=[
        DocumentRowEnum.HEADER,
        DocumentRowEnum.TOTAL_SCORE
    ]
)