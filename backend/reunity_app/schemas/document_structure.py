from pydantic import BaseModel
from typing import List, Dict, Any
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

class DocumentRowUpdate(BaseModel):
    row_name: DocumentRowEnum
    values: List[str]  # [label, before, after]

class DocumentContent(BaseModel):
    table_data: Dict[str, List[str]]
    neurologist_completed: bool = False
    therapist_completed: bool = False
    head_completed: bool = False

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