from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import enum
from datetime import datetime

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


class Patient(Base):
    """Модель пациента"""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    last_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    birth_date = Column(DateTime)
    insurance_number = Column(String(20))  # Последние 4 цифры полиса
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

    content = Column(JSON, default=dict, nullable=False)

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