from sqlalchemy.orm import Session
from typing import Optional
from app.models import AuditLog

def record_audit_log(
    db: Session,
    user_id: Optional[int],
    action: str,
    document_id: Optional[int] = None,
    details: Optional[str] = None
) -> AuditLog:
    """
    Adds an audit log entry to the current SQLAlchemy transaction session.
    Does NOT call db.commit() on its own so callers can commit atomically.
    """
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        document_id=document_id,
        details=details
    )
    db.add(log_entry)
    return log_entry
