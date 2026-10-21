from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import AuditLog, Document, User
from app.schemas import PaginatedAuditLogs
from app.utils.security import get_current_user

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

@router.get("", response_model=PaginatedAuditLogs)
def get_audit_logs(
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Users can view logs for actions they performed OR actions performed on documents they own
    owned_doc_ids = db.query(Document.id).filter(Document.owner_id == current_user.id)
    query = db.query(AuditLog).filter(
        or_(AuditLog.user_id == current_user.id, AuditLog.document_id.in_(owned_doc_ids))
    )

    if action:
        query = query.filter(AuditLog.action == action.upper())
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if document_id:
        query = query.filter(AuditLog.document_id == document_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size).all()

    items = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "user_email": log.user.email if log.user else None,
            "action": log.action,
            "document_id": log.document_id,
            "details": log.details,
            "created_at": log.created_at
        }
        for log in logs
    ]

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items
    }
