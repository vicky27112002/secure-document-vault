from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ShareCreate(BaseModel):
    user_email: EmailStr
    permission: str = Field(default="DOWNLOAD", pattern="^(VIEW|DOWNLOAD)$")

class ShareResponse(BaseModel):
    id: int
    document_id: int
    shared_with_user_id: int
    shared_with_email: str
    permission: str
    created_at: datetime

class DocumentResponse(BaseModel):
    id: int
    owner_id: int
    owner_email: str
    original_filename: str
    mime_type: str
    file_size: int
    encryption_version: str
    access_role: str # OWNER, VIEW, or DOWNLOAD
    created_at: datetime
    shares: List[ShareResponse] = []

class PaginatedDocuments(BaseModel):
    total: int
    page: int
    size: int
    items: List[DocumentResponse]

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_email: Optional[str]
    action: str
    document_id: Optional[int]
    details: Optional[str]
    created_at: datetime

class PaginatedAuditLogs(BaseModel):
    total: int
    page: int
    size: int
    items: List[AuditLogResponse]
