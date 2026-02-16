from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import enum
from datetime import datetime
from typing import List, Dict, Any  # Важный импорт!
from sqlalchemy.orm.attributes import flag_modified
from .base import Base


class DoctorRole(str, enum.Enum):
    """Роли врачей"""
    THERAPIST = "therapist"
    NEUROLOGIST = "neurologist"
    HEAD = "head"
    ADMIN = "admin"


class CaseStatus(str, enum.Enum):
    """Статусы случая"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    SENT = "sent"
    ARCHIVED = "archived"


class DocumentRow(str, enum.Enum):
    """Строки документа"""
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


# Константы для распределения строк по врачам
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
    """Модель пациента"""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    birth_date = Column(DateTime)
    insurance_number = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    cases = relationship("Case", back_populates="patient", cascade="all, delete-orphan")

    @validates('last_name', 'first_name')
    def validate_name(self, key, value):
        """Валидация ФИО"""
        if not value or not value.strip():
            raise ValueError(f"{key} не может быть пустым")
        return value.strip()

    def __repr__(self):
        return f"<Patient {self.last_name} {self.first_name}>"

    @property
    def full_name(self):
        """Полное имя пациента"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)


class Doctor(Base):
    """Модель врача"""
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    role = Column(Enum(DoctorRole), nullable=False, default=DoctorRole.THERAPIST)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    created_cases = relationship("Case", back_populates="creator")
    document_sections = relationship("DocumentSection", back_populates="doctor")
    signed_documents = relationship("Document", back_populates="signer")

    def __repr__(self):
        return f"<Doctor {self.last_name} {self.first_name} ({self.role})>"

    @property
    def full_name(self):
        """Полное имя врача"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)


class DocumentTemplate(Base):
    """Шаблон документа"""
    __tablename__ = "document_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    structure = Column(JSON, nullable=False, default=dict)
    webmis_template_id = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Case(Base):
    """Случай (приём пациента)"""
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

    # Связи
    patient = relationship("Patient", back_populates="cases")
    creator = relationship("Doctor", back_populates="created_cases")
    document = relationship("Document", back_populates="case", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Case #{self.id} {self.status}>"


class Document(Base):
    """Документ (заключение)"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("document_templates.id"))
    signer_id = Column(Integer, ForeignKey("doctors.id"))

    # Структура документа в виде JSON-таблицы
    content = Column(JSON, default={}, nullable=False)

    # Статусы заполнения врачами
    neurologist_completed = Column(Boolean, default=False)
    therapist_completed = Column(Boolean, default=False)
    head_completed = Column(Boolean, default=False)

    # Даты заполнения
    neurologist_filled_at = Column(DateTime(timezone=True))
    therapist_filled_at = Column(DateTime(timezone=True))
    head_filled_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    signed_at = Column(DateTime(timezone=True))

    # Связи
    case = relationship("Case", back_populates="document")
    template = relationship("DocumentTemplate")
    signer = relationship("Doctor", back_populates="signed_documents")
    sections = relationship("DocumentSection", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document #{self.id}>"

    def initialize_content(self):
        """Инициализация структуры документа"""
        self.content = {
            "header": ["Дата", "", ""],
            "pain_syndrome": ["Болевой синдром", "", ""],
            "stato_dynamic": ["Нарушение стато-динамических функций", "", ""],
            "mental_functions": ["Нарушение психических функций: восприятия, памяти, мышления, речи, эмоции, воли", "",
                                 ""],
            "internal_organs": [
                "Нарушение функций: кровообращения, дыхания, пищеварения, выделения, обмена веществ и энергии, внутренней секреции",
                "", ""],
            "sensory_functions": ["Нарушение зрительных функций: зрения, слуха, обоняния, осязания", "", ""],
            "vital_activity": ["Нарушение жизнедеятельности", "", ""],
            "self_care": ["Нарушение самообслуживания", "", ""],
            "mobility": ["Нарушение способности к передвижению", "", ""],
            "work_ability": ["Нарушение способности к трудовой деятельности", "", ""],
            "communication": ["Нарушение способности к общению с окружающими", "", ""],
            "total_score": ["Сумма баллов", "", ""]
        }

    from sqlalchemy.orm.attributes import flag_modified

    def update_row(self, row_name: DocumentRow, values: List[str]):
        """Обновление строки документа"""
        if row_name.value in self.content:
            if len(values) == 3:
                self.content[row_name.value] = values
            else:
                # Обновляем только значения, не меняя название строки
                current_row = self.content.get(row_name.value, ["", "", ""])
                if len(values) >= 2:
                    current_row[1] = values[0] if len(values) > 0 else ""
                    current_row[2] = values[1] if len(values) > 1 else ""
                self.content[row_name.value] = current_row

        # ВАЖНО: Помечаем поле как измененное
        flag_modified(self, "content")

        # Выводим отладочную информацию
        print(f"📝 Обновление строки {row_name.value}: {values}")
        print(f"   Новый content: {self.content[row_name.value]}")

    def update_row_string(self, row_name: str, values: List[str]):
        """Обновление строки документа по строковому имени"""
        if row_name in self.content:
            current_row = self.content.get(row_name, ["", "", ""])
            if len(values) >= 2:
                current_row[1] = values[0] if len(values) > 0 else ""
                current_row[2] = values[1] if len(values) > 1 else ""
            self.content[row_name] = current_row

        # ВАЖНО: Помечаем поле как измененное
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(self, "content")

        print(f"📝 Обновление строки {row_name}: {values}")
        print(f"   Новый content: {self.content[row_name]}")

    def calculate_total_score(self):
        """Расчет итогового балла"""
        total_before = 0
        total_after = 0

        for row in DocumentRow:
            if row in [DocumentRow.HEADER, DocumentRow.TOTAL_SCORE]:
                continue

            row_data = self.content.get(row.value, ["", "", ""])
            try:
                if row_data[1]:  # "До лечения"
                    total_before += int(row_data[1])
                if row_data[2]:  # "После лечения"
                    total_after += int(row_data[2])
            except ValueError:
                continue

        self.content["total_score"] = ["Сумма баллов", str(total_before), str(total_after)]


class DocumentSection(Base):
    """Раздел документа, заполненный конкретным врачом"""
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

    # Связи
    document = relationship("Document", back_populates="sections")
    doctor = relationship("Doctor", back_populates="document_sections")

    def __repr__(self):
        return f"<DocumentSection {self.section_name} by Dr#{self.doctor_id}>"


class WebmisFieldMapping(Base):
    """Маппинг полей нашего документа на поля в ВебМИС"""
    __tablename__ = "webmis_field_mapping"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("document_templates.id"), nullable=False)
    our_field_name = Column(String(100), nullable=False)
    webmis_field_id = Column(String(100), nullable=False)
    description = Column(String(255))
    required = Column(Boolean, default=True)
    order = Column(Integer, default=0)

    template = relationship("DocumentTemplate")