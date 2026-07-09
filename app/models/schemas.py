from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Any, Dict, List

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


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


class SourceReference(BaseModel):
    source_file: str
    classification: ClassificationEnum
    score: float | None = None


class SearchResponse(BaseModel):
    query: str
    response: str
    access_clearance_applied: ClassificationEnum
    sources_consulted: List[SourceReference]
