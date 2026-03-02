from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import enum
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm.attributes import flag_modified
from .base import Base


class DoctorRole(str, enum.Enum):
    """Роли врачей"""
    REFLEXOTHERAPIST = "reflexotherapist"      # Рефлексотерапевт
    PHYSIOTHERAPIST = "physiotherapist"        # Физиотерапевт
    THERAPIST_FRM = "therapist_frm"             # Терапевт/Врач ФРМ
    NEUROLOGIST_FRM = "neurologist_frm"         # Невролог/Врач ФРМ
    PSYCHOLOGIST = "psychologist"               # Психолог
    ADMIN = "admin"                              # Администратор


class CaseStatus(str, enum.Enum):
    """Статусы случая"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    SENT = "sent"
    ARCHIVED = "archived"


class DocumentRow(str, enum.Enum):
    """Строки документа (для обратной совместимости с предыдущей версией)"""
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


# Константы для распределения строк по врачам (старые) – могут быть удалены позже
NEUROLOGIST_ROWS = [
    DocumentRow.PAIN_SYNDROME,
    DocumentRow.STATO_DYNAMIC,
    DocumentRow.MENTAL_FUNCTIONS,
    DocumentRow.INTERNAL_ORGANS,
    DocumentRow.SENSORY_FUNCTIONS
]

THERAPIST_ROWS = [
    DocumentRow.VITAL_ACTIVITY,
    DocumentRow.SELF_CARE,
    DocumentRow.MOBILITY,
    DocumentRow.WORK_ABILITY,
    DocumentRow.COMMUNICATION
]

HEAD_ROWS = [
    DocumentRow.HEADER,
    DocumentRow.TOTAL_SCORE
]


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    birth_date = Column(DateTime)
    insurance_number = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cases = relationship("Case", back_populates="patient", cascade="all, delete-orphan")

    @validates('last_name', 'first_name')
    def validate_name(self, key, value):
        if not value or not value.strip():
            raise ValueError(f"{key} не может быть пустым")
        return value.strip()

    def __repr__(self):
        return f"<Patient {self.last_name} {self.first_name}>"

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    role = Column(
        Enum(DoctorRole, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=DoctorRole.THERAPIST_FRM
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    created_cases = relationship("Case", back_populates="creator")
    document_sections = relationship("DocumentSection", back_populates="doctor")
    signed_documents = relationship("Document", back_populates="signer")

    def __repr__(self):
        return f"<Doctor {self.last_name} {self.first_name} ({self.role})>"

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    structure = Column(JSON, nullable=False, default=dict)
    webmis_template_id = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    status = Column(Enum(CaseStatus), default=CaseStatus.DRAFT, nullable=False)
    admission_date = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))
    sent_to_webmis_at = Column(DateTime(timezone=True))

    patient = relationship("Patient", back_populates="cases")
    creator = relationship("Doctor", back_populates="created_cases")
    document = relationship("Document", back_populates="case", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Case #{self.id} {self.status}>"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("document_templates.id"))
    signer_id = Column(Integer, ForeignKey("doctors.id"))

    content = Column(JSON, default={}, nullable=False)

    # Статусы заполнения врачами
    reflexotherapist_completed = Column(Boolean, default=False)
    physiotherapist_completed = Column(Boolean, default=False)
    therapist_frm_completed = Column(Boolean, default=False)      # бывший therapist_completed
    neurologist_frm_completed = Column(Boolean, default=False)    # бывший neurologist_completed
    psychologist_completed = Column(Boolean, default=False)

    # Даты заполнения
    reflexotherapist_filled_at = Column(DateTime(timezone=True))
    physiotherapist_filled_at = Column(DateTime(timezone=True))
    therapist_frm_filled_at = Column(DateTime(timezone=True))
    neurologist_frm_filled_at = Column(DateTime(timezone=True))
    psychologist_filled_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    signed_at = Column(DateTime(timezone=True))

    case = relationship("Case", back_populates="document")
    template = relationship("DocumentTemplate")
    signer = relationship("Doctor", back_populates="signed_documents")
    sections = relationship("DocumentSection", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document #{self.id}>"

    def initialize_content(self):
        # Полный список строк из реального документа, включая заголовки разделов
        ALL_ROWS = [
            # --- Глобальные умственные функции ---
            {"id": "section_global_mental", "label": "Глобальные умственные функции (b110-b139)", "is_section": True},
            {"id": "b110", "label": "b110 Функции сознания"},
            {"id": "b114", "label": "b114 Функции ориентированности"},
            {"id": "b117", "label": "b117 Интеллектуальные функции"},
            {"id": "b134", "label": "b134 Функции сна"},
            {"id": "b1343", "label": "b1343 Качество сна"},
            {"id": "b139", "label": "b139 Глобальные умственные функции, другие уточненные и не уточненные"},

            # --- Специфические умственные функции ---
            {"id": "section_specific_mental", "label": "Специфические умственные функции (b140-b189)", "is_section": True},
            {"id": "b140", "label": "b140 Функции внимания"},
            {"id": "b144", "label": "b144 Функция памяти"},
            {"id": "b147", "label": "b147 Психомоторные функции"},
            {"id": "b152", "label": "b152 Функции эмоций"},
            {"id": "b156", "label": "b156 Функции восприятия"},
            {"id": "b160", "label": "b160 Функции мышления"},
            {"id": "b164", "label": "b164 Познавательные функции высокого уровня"},
            {"id": "b167", "label": "b167 Умственные функции речи"},
            {"id": "b172", "label": "b172 Функции вычисления"},
            {"id": "b176", "label": "b176 умственные функции последовательных сложных движений"},
            {"id": "b180", "label": "b180 Функции самоощущения и ощущения времени"},
            {"id": "b199", "label": "b199 Умственные функции, не уточненные"},

            # --- Зрение и связанные с ним функции ---
            {"id": "section_vision", "label": "Зрение и связанные с ним функции (b210-b229)", "is_section": True},
            {"id": "b210", "label": "b210 Функции зрения"},

            # --- Слух и вестибулярные функции ---
            {"id": "section_hearing", "label": "Слух и вестибулярные функции (b230-b249)", "is_section": True},
            {"id": "b230", "label": "b230 Функции слуха"},
            {"id": "b240", "label": "b240 Ощущения, связанные со слухом и вестибулярным аппаратом"},
            {"id": "b255", "label": "b255 Функции обоняния"},
            {"id": "b265", "label": "b265 Функции осязания (онемение)"},
            {"id": "b270", "label": "b270 Сенсорные функции, связанные с температурой и другими раздражителями"},

            # --- Боль ---
            {"id": "section_pain", "label": "Боль (b280-289)", "is_section": True},
            {"id": "b280", "label": "b280 Ощущение боли"},
            {"id": "b2801", "label": "b2801 Боль в части тела"},
            {"id": "b28013", "label": "b28013 Боль в спине"},
            {"id": "b28014", "label": "b28014 Боль в верхней конечности"},
            {"id": "b28010", "label": "b28010 Боль в голове и шее"},
            {"id": "b28011", "label": "b28011 Боль в грудной клетке"},
            {"id": "b28015", "label": "b28015 Боль в нижней конечности"},
            {"id": "b28016", "label": "b28016 Боль в суставах"},
            {"id": "b289", "label": "b289 Ощущение боли, другое уточненное и не уточненное"},

            # --- Функции сердечно-сосудистой системы ---
            {"id": "section_cardiovascular", "label": "Функции сердечно-сосудистой системы (b410-b429)", "is_section": True},
            {"id": "b410", "label": "b410 Функции сердца"},
            {"id": "b4101", "label": "b4101 Ритм сердечных сокращений"},
            {"id": "b4102", "label": "b4102 Сократительная сила миокарда желудочков"},
            {"id": "b4103", "label": "b4103 Кровоснабжение сердца"},
            {"id": "b415", "label": "b415 Функции кровеносных сосудов"},
            {"id": "b4150", "label": "b4150 Функции артерий"},
            {"id": "b4152", "label": "b4152 Функции вен"},
            {"id": "b420", "label": "b420 Функции артериального давления"},
            {"id": "b4200", "label": "b4200 Повышение артериального давления"},
            {"id": "b4202", "label": "b4202 Поддержание артериального давления"},
            {"id": "b4550", "label": "b4550 Общая физическая выносливость"},
            {"id": "b4552", "label": "b4552 Утомляемость"},
            {"id": "b460", "label": "b460 Ощущения, связанные с функционированием сердечно-сосудистой и дыхательной систем"},

            # --- Функции пищеварительной и эндокринной систем ---
            {"id": "section_digestive", "label": "Функции пищеварительной и эндокринной систем (b525-b540)", "is_section": True},
            {"id": "b525", "label": "b525 Функции дефекации (запор)"},
            {"id": "b530", "label": "b530 Функции сохранения массы тела"},
            {"id": "b5401", "label": "b5401 Углеводный обмен"},

            # --- Урогенитальные и репродуктивные функции ---
            {"id": "section_urogenital", "label": "Урогенитальные и репродуктивные функции (b610-b630)", "is_section": True},
            {"id": "b620", "label": "b620 Функции мочеиспускания"},
            {"id": "b6200", "label": "b6200 Мочеиспускание"},

            # --- Функции суставов и костей ---
            {"id": "section_joints", "label": "Функции суставов и костей (b710-b729)", "is_section": True},
            {"id": "b710", "label": "b710 Функции подвижности сустава"},
            {"id": "b7100", "label": "b7100 Подвижность одного сустава"},
            {"id": "b7101", "label": "b7101 Подвижность нескольких суставов"},
            {"id": "b715", "label": "b715 Функции стабильного сустава"},
            {"id": "b720", "label": "b720 Функции подвижности костного аппарата"},
            {"id": "b729", "label": "b729 Функции суставов и костей, другие уточненные и не уточненные"},

            # --- Функции мышц ---
            {"id": "section_muscles", "label": "Функции мышц (b730-b749)", "is_section": True},
            {"id": "b730", "label": "b730 Функции мышечной силы"},
            {"id": "b7302", "label": "b7302 Сила мышц одной стороны тела"},
            {"id": "b735", "label": "b735 Функции мышечного тонуса"},
            {"id": "b740", "label": "b740 Функции мышечной выносливости"},
            {"id": "b749", "label": "b749 Функции мышц, другие уточненные и не уточненные"},

            # --- Двигательные функции ---
            {"id": "section_motor", "label": "Двигательные функции (b750-b789)", "is_section": True},
            {"id": "b750", "label": "b750 Моторно-рефлекторные функции"},
            {"id": "b755", "label": "b755 Функции непроизвольной двигательной реакции"},
            {"id": "b760", "label": "b760 Контроль произвольных двигательных функций"},
            {"id": "b7651", "label": "b7651 Тремор"},
            {"id": "b770", "label": "b770 Функции стереотипа походки"},
            {"id": "b789", "label": "b789 Двигательные функции, другие уточненные и не уточненные"},
            {"id": "b7800", "label": "b7800 Ощущение мышечной скованности"},
            {"id": "b7801", "label": "b7801 Ощущение мышечного спазма"},

            # --- Структуры организма (s-коды) ---
            {"id": "section_structures", "label": "Структуры организма", "is_section": True},
            {"id": "s110", "label": "s110 Структура головного мозга"},
            {"id": "s120", "label": "s120 Спинной мозг и относящиеся к нему структуры"},
            {"id": "s130", "label": "s130 Структура мозговых оболочек"},
            {"id": "s140", "label": "s140 Структура симпатической нервной системы"},
            {"id": "s150", "label": "s150 Структура парасимпатической нервной системы"},
            {"id": "s198", "label": "s198 Структура нервной системы, другая уточненная"},
            {"id": "s199", "label": "s199 Структура нервной системы, не уточненная"},

            {"id": "s4100", "label": "s4100 Сердце"},
            {"id": "s41000", "label": "s41000 Предсердия"},
            {"id": "s41001", "label": "s41001 Желудочки"},
            {"id": "s4101", "label": "s4101 Артерии"},
            {"id": "s4102", "label": "s4102 Вены"},
            {"id": "s610", "label": "s610 Структура мочевыделительной системы"},
            {"id": "s620", "label": "s620 Структура тазового дна"},
            {"id": "s630", "label": "s630 Структура репродуктивной системы"},

            {"id": "s710", "label": "s710 Структура головы и области шеи"},
            {"id": "s720", "label": "s720 Структура области плеча"},
            {"id": "s7200", "label": "s7200 Кости плечевого пояса"},
            {"id": "s730", "label": "s730 Структура верхней конечности"},
            {"id": "s7300", "label": "s7300 Структура плеча"},
            {"id": "s73002", "label": "s73002 Мышца плеча"},
            {"id": "s7301", "label": "s7301 Структура предплечья"},
            {"id": "s7302", "label": "s7302 Структура кисти"},
            {"id": "s740", "label": "s740 Структура тазовой области"},
            {"id": "s750", "label": "s750 Структура нижней конечности"},
            {"id": "s7500", "label": "s7500 Структура бедра"},
            {"id": "s75001", "label": "s75001 Тазобедренный сустав"},
            {"id": "s75011", "label": "s75011 Коленный сустав"},
            {"id": "s5001", "label": "s5001 Структура голени"},
            {"id": "s7502", "label": "s7502 Структура лодыжки и стопы"},
            {"id": "s760", "label": "s760 Структура туловища"},
            {"id": "s7600", "label": "s7600 Структура позвоночника"},
            {"id": "s76002", "label": "s76002 Поясничный отдел позвоночника"},
            {"id": "s770", "label": "s770 Дополнительные скелетно-мышечные структуры, связанные с движением"},
            {"id": "s798", "label": "s798 Структуры, связанные с движением, другие уточненные"},

            # --- Активность и участие (d-коды) ---
            {"id": "section_activity", "label": "Активность и участие", "is_section": True},
            {"id": "d330", "label": "d330 Речь"},
            {"id": "d350", "label": "d350 Разговор"},
            {"id": "d410", "label": "d410 Изменение позы тела"},
            {"id": "d415", "label": "d415 Поддержание положения тела"},
            {"id": "d420", "label": "d420 Перемещение тела"},
            {"id": "d429", "label": "d429 Изменение и поддержание положения тела, другое уточненное и не уточненное"},
            {"id": "d430", "label": "d430 Поднятие и перенос объектов"},
            {"id": "d435", "label": "d435 Перемещение объектов ногами"},
            {"id": "d440", "label": "d440 Использование точных движений кисти"},
            {"id": "d445", "label": "d445 Использование кисти и руки"},
            {"id": "d449", "label": "d449 Перенос, перемещение и манипулирование объектами, другое уточненное и не уточненное"},
            {"id": "d450", "label": "d450 Ходьба"},
            {"id": "d465", "label": "d465 Передвижение с использованием технических средств"},
            {"id": "d469", "label": "d469 Ходьба, передвижение и относящаяся к ним активность, другие уточненные и не уточненные"},
            {"id": "d499", "label": "d499 Мобильность, не уточненная"},
            {"id": "d5701", "label": "d5701 Соблюдение диеты"},
        ]

        # Таблица процедур (план реабилитационных мероприятий)
        PROCEDURE_TABLE_ROWS = [
            {"id": "manual_therapy", "label": "Мануальная терапия"},
            {"id": "massage", "label": "Массаж"},
            {"id": "acupuncture", "label": "Иглорефлексотерапия"},
            {"id": "mri", "label": "МРТ"},
            {"id": "mechanotherapy", "label": "Механотерапия"},
            {"id": "exercise_therapy", "label": "ЛФК"},
            {"id": "laser_therapy", "label": "Лазеротерапия"},
            {"id": "electrophoresis", "label": "Электрофорез"},
            {"id": "electrostimulation", "label": "Электростимуляция"},
            {"id": "magnetotherapy", "label": "Магнитотерапия"},
            {"id": "electrosleep", "label": "Электросон"},
            {"id": "psychological_counseling", "label": "Психологическое консультирование/СПЭР"},
            {"id": "biofeedback", "label": "БОС-терапия"},
        ]

        self.content = {
            "diagnosis_mkb": "",
            "rehab_potential": "",
            "rehab_prognosis": "",
            "table_dates": {
                "admission": "",
                "intermediate": "",
                "discharge": ""
            },
            "main_table": {
                "rows": [
                    {
                        "id": row["id"],
                        "label": row["label"],
                        "is_section": row.get("is_section", False),
                        "values": ["", "", "", ""] if not row.get("is_section", False) else []
                    }
                    for row in ALL_ROWS
                ]
            },
            "goals": {
                "short_term": "",
                "long_term": ""
            },
            "procedures_table": {
                "rows": [
                    {
                        "id": row["id"],
                        "label": row["label"],
                        "values": ["", ""]
                    }
                    for row in PROCEDURE_TABLE_ROWS
                ]
            }
        }
        # Инициализируем 5 пустых дополнительных строк
        self.initialize_additional_domains()

    def initialize_additional_domains(self, count=5):
        """
        Инициализирует массив дополнительных доменов.
        По умолчанию создаётся 5 пустых строк.
        """
        if "additional_domains" not in self.content:
            self.content["additional_domains"] = [
                {"name": "", "admission": "", "intermediate": "", "discharge": "", "note": ""}
                for _ in range(count)
            ]
            flag_modified(self, "content")

    def update_additional_row(self, index: int, row_data: dict):
        """
        Обновляет одну строку дополнительных доменов.
        row_data должен содержать ключи: name, admission, intermediate, discharge, note.
        """
        if "additional_domains" not in self.content:
            self.initialize_additional_domains()
        rows = self.content["additional_domains"]
        if 0 <= index < len(rows):
            rows[index].update(row_data)
            flag_modified(self, "content")
        else:
            raise IndexError("Index out of range")

    def add_additional_row(self, row_data: dict = None):
        """Добавляет новую пустую строку в конец массива дополнительных доменов."""
        if "additional_domains" not in self.content:
            self.initialize_additional_domains()
        default = {"name": "", "admission": "", "intermediate": "", "discharge": "", "note": ""}
        if row_data:
            default.update(row_data)
        self.content["additional_domains"].append(default)
        flag_modified(self, "content")

    def remove_additional_row(self, index: int):
        """Удаляет строку по индексу."""
        if "additional_domains" in self.content and 0 <= index < len(self.content["additional_domains"]):
            del self.content["additional_domains"][index]
            flag_modified(self, "content")

    def update_main_table_row(self, row_id: str, values: List[str]):
        if "main_table" not in self.content:
            self.content["main_table"] = {"rows": []}
        for row in self.content["main_table"]["rows"]:
            if row["id"] == row_id:
                if row.get("is_section", False):
                    return
                if len(values) == 4:
                    row["values"] = values
                else:
                    current = row["values"]
                    for i in range(len(values)):
                        current[i] = values[i]
                flag_modified(self, "content")
                return
        if not any(row.get("is_section", False) for row in self.content["main_table"]["rows"] if row["id"] == row_id):
            self.content["main_table"]["rows"].append({
                "id": row_id,
                "label": row_id,
                "is_section": False,
                "values": values if len(values) == 4 else ["", "", "", ""]
            })
            flag_modified(self, "content")

    def update_procedure_row(self, row_id: str, values: List[str]):
        if "procedures_table" not in self.content:
            self.content["procedures_table"] = {"rows": []}
        for row in self.content["procedures_table"]["rows"]:
            if row["id"] == row_id:
                if len(values) == 2:
                    row["values"] = values
                else:
                    current = row["values"]
                    for i in range(len(values)):
                        current[i] = values[i]
                flag_modified(self, "content")
                return
        self.content["procedures_table"]["rows"].append({
            "id": row_id,
            "label": row_id,
            "values": values if len(values) == 2 else ["", ""]
        })
        flag_modified(self, "content")

    def update_header_field(self, field_name: str, value: str):
        if field_name in ["diagnosis_mkb", "rehab_potential", "rehab_prognosis"]:
            self.content[field_name] = value
            flag_modified(self, "content")

    def update_table_dates(self, admission: str = None, intermediate: str = None, discharge: str = None):
        if "table_dates" not in self.content:
            self.content["table_dates"] = {"admission": "", "intermediate": "", "discharge": ""}
        if admission is not None:
            self.content["table_dates"]["admission"] = admission
        if intermediate is not None:
            self.content["table_dates"]["intermediate"] = intermediate
        if discharge is not None:
            self.content["table_dates"]["discharge"] = discharge
        flag_modified(self, "content")

    def update_goals(self, short_term: str = None, long_term: str = None):
        if "goals" not in self.content:
            self.content["goals"] = {"short_term": "", "long_term": ""}
        if short_term is not None:
            self.content["goals"]["short_term"] = short_term
        if long_term is not None:
            self.content["goals"]["long_term"] = long_term
        flag_modified(self, "content")

    def update_row(self, row_name: DocumentRow, values: List[str]):
        if row_name.value in self.content:
            if len(values) == 3:
                self.content[row_name.value] = values
            else:
                current_row = self.content.get(row_name.value, ["", "", ""])
                if len(values) >= 2:
                    current_row[1] = values[0] if len(values) > 0 else ""
                    current_row[2] = values[1] if len(values) > 1 else ""
                self.content[row_name.value] = current_row
        flag_modified(self, "content")

    def update_row_string(self, row_name: str, values: List[str]):
        if row_name in self.content:
            current_row = self.content.get(row_name, ["", "", ""])
            if len(values) >= 2:
                current_row[1] = values[0] if len(values) > 0 else ""
                current_row[2] = values[1] if len(values) > 1 else ""
            self.content[row_name] = current_row
        flag_modified(self, "content")

    def calculate_total_score(self):
        total_before = 0
        total_after = 0
        for row in DocumentRow:
            if row in [DocumentRow.HEADER, DocumentRow.TOTAL_SCORE]:
                continue
            row_data = self.content.get(row.value, ["", "", ""])
            try:
                if row_data[1]:
                    total_before += int(row_data[1])
                if row_data[2]:
                    total_after += int(row_data[2])
            except ValueError:
                continue
        self.content["total_score"] = ["Сумма баллов", str(total_before), str(total_after)]


class DocumentSection(Base):
    __tablename__ = "document_sections"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    section_name = Column(String(50), nullable=False)
    content = Column(JSON, default=dict, nullable=False)
    is_signed = Column(Boolean, default=False)
    signed_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    document = relationship("Document", back_populates="sections")
    doctor = relationship("Doctor", back_populates="document_sections")

    def __repr__(self):
        return f"<DocumentSection {self.section_name} by Dr#{self.doctor_id}>"


class WebmisFieldMapping(Base):
    __tablename__ = "webmis_field_mapping"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("document_templates.id"), nullable=False)
    our_field_name = Column(String(100), nullable=False)
    webmis_field_id = Column(String(100), nullable=False)
    description = Column(String(255))
    required = Column(Boolean, default=True)
    order = Column(Integer, default=0)

    template = relationship("DocumentTemplate")