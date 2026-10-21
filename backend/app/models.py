from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(255), unique=True, nullable=False) # Internal UUID, never exposed as path
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    encryption_version = Column(String(32), nullable=False, default="v1_aes_256_gcm")
    nonce_hex = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    owner = relationship("User", back_populates="documents")
    shares = relationship("DocumentShare", back_populates="document", cascade="all, delete-orphan")


class DocumentShare(Base):
    __tablename__ = "document_shares"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_with_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission = Column(String(32), nullable=False, default="DOWNLOAD") # VIEW or DOWNLOAD
    created_at = Column(DateTime(timezone=True), default=utc_now)

    document = relationship("Document", back_populates="shares")
    shared_user = relationship("User")

    __table_args__ = (
        UniqueConstraint("document_id", "shared_with_user_id", name="uq_document_user_share"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True) # LOGIN, UPLOAD, DOWNLOAD, SHARE, REVOKE, DELETE
    document_id = Column(Integer, nullable=True, index=True)
    details = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    user = relationship("User")
