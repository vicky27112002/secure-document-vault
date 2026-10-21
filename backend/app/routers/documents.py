import io
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import User, Document, DocumentShare
from app.schemas import DocumentResponse, PaginatedDocuments, ShareCreate, ShareResponse
from app.utils.security import get_current_user
from app.services.document_service import (
    upload_and_encrypt_document,
    get_authorized_document,
    download_and_decrypt_document,
    share_document_service,
    revoke_share_service,
    delete_document_service,
    serialize_document
)

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return upload_and_encrypt_document(db, current_user, file)

@router.get("", response_model=PaginatedDocuments)
def list_documents(
    search: Optional[str] = Query(None),
    mime_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shared_doc_ids = db.query(DocumentShare.document_id).filter(
        DocumentShare.shared_with_user_id == current_user.id
    )
    query = db.query(Document).filter(
        or_(Document.owner_id == current_user.id, Document.id.in_(shared_doc_ids))
    )

    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))
    if mime_type:
        query = query.filter(Document.mime_type == mime_type)
    if start_date:
        query = query.filter(Document.created_at >= start_date)
    if end_date:
        query = query.filter(Document.created_at <= end_date)

    total = query.count()
    docs = query.order_by(Document.created_at.desc()).offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [serialize_document(d, current_user.id) for d in docs]
    }

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document_metadata(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = get_authorized_document(db, doc_id, current_user, require_download=False)
    return serialize_document(doc, current_user.id)

@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc, plaintext = download_and_decrypt_document(db, doc_id, current_user)
    return StreamingResponse(
        io.BytesIO(plaintext),
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'}
    )

@router.post("/{doc_id}/share", response_model=ShareResponse)
def share_document(
    doc_id: int,
    payload: ShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return share_document_service(db, doc_id, current_user, payload.user_email, payload.permission)

@router.delete("/{doc_id}/share/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_document_access(
    doc_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    revoke_share_service(db, doc_id, current_user, user_id)
    return None

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    delete_document_service(db, doc_id, current_user)
    return None
