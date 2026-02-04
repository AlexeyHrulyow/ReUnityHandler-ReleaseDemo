from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List


class DocumentBase(BaseModel):
    case_id: int
    template_id: Optional[int] = None
    content: Dict[str, Any] = {}


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    content: Optional[Dict[str, Any]] = None
    signer_id: Optional[int] = None
    signed_at: Optional[datetime] = None


class Document(DocumentBase):
    id: int
    signer_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentWithDetails(Document):
    case_info: Optional[Dict[str, Any]] = None
    template_name: Optional[str] = None
    signer_name: Optional[str] = None


class DocumentSectionBase(BaseModel):
    document_id: int
    doctor_id: int
    section_name: str
    content: Dict[str, Any] = {}
    is_signed: bool = False


class DocumentSectionCreate(DocumentSectionBase):
    pass


class DocumentSectionUpdate(BaseModel):
    content: Optional[Dict[str, Any]] = None
    is_signed: Optional[bool] = None
    signed_at: Optional[datetime] = None


class DocumentSection(DocumentSectionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentSectionWithDetails(DocumentSection):
    doctor_name: Optional[str] = None
    document_info: Optional[Dict[str, Any]] = None