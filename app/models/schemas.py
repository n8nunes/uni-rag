from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Dict, Any

class ClassificationEnum(str, Enum):
    PUBLIC = "Public"
    RESTRICTED = "Restricted-Internal"
    STUDENT_ONLY = "Student-Only"

class UserSession(BaseModel):
    user_id: str
    username: str
    role: str
    clearance_level: ClassificationEnum

class DocumentMetadata(BaseModel):
    source_file: str
    classification: ClassificationEnum
    uploaded_by: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")