import os
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import UploadFile, HTTPException, status
from app.config import settings
from app.models import Document, DocumentShare, User
from app.services.encryption_service import EncryptionService
from app.services.audit_service import record_audit_log
from app.utils.validators import validate_upload_file

def get_encrypted_file_path(storage_key: str) -> str:
    return os.path.join(settings.STORAGE_DIR, f"{storage_key}.enc")

def serialize_document(doc: Document, current_user_id: int) -> dict:
    if doc.owner_id == current_user_id:
        role = "OWNER"
    else:
        share = next((s for s in doc.shares if s.shared_with_user_id == current_user_id), None)
        role = share.permission if share else "NONE"

    shares_list = []
    if doc.owner_id == current_user_id:
        for s in doc.shares:
            shares_list.append({
                "id": s.id,
                "document_id": s.document_id,
                "shared_with_user_id": s.shared_with_user_id,
                "shared_with_email": s.shared_user.email if s.shared_user else "",
                "permission": s.permission,
                "created_at": s.created_at
            })

    return {
        "id": doc.id,
        "owner_id": doc.owner_id,
        "owner_email": doc.owner.email if doc.owner else "",
        "original_filename": doc.original_filename,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "encryption_version": doc.encryption_version,
        "access_role": role,
        "created_at": doc.created_at,
        "shares": shares_list
    }

def upload_and_encrypt_document(db: Session, user: User, file: UploadFile) -> dict:
    plaintext = file.file.read()
    validate_upload_file(file, plaintext)

    ciphertext, nonce_hex, enc_version = EncryptionService.encrypt_bytes(plaintext)
    storage_key = uuid.uuid4().hex
    file_path = get_encrypted_file_path(storage_key)

    try:
        # Write ONLY encrypted ciphertext to disk (plaintext is never written to disk)
        with open(file_path, "wb") as f:
            f.write(ciphertext)

        doc = Document(
            owner_id=user.id,
            original_filename=file.filename,
            storage_key=storage_key,
            mime_type=file.content_type,
            file_size=len(plaintext),
            encryption_version=enc_version,
            nonce_hex=nonce_hex
        )
        db.add(doc)
        db.flush() # Obtain doc.id before committing

        record_audit_log(
            db=db,
            user_id=user.id,
            action="UPLOAD",
            document_id=doc.id,
            details=f"Uploaded and encrypted '{file.filename}' ({len(plaintext)} bytes)"
        )
        db.commit()
        db.refresh(doc)
        return serialize_document(doc, user.id)
    except Exception as exc:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise exc

def get_authorized_document(db: Session, doc_id: int, user: User, require_download: bool = False) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc.owner_id == user.id:
        return doc

    share = db.query(DocumentShare).filter(
        DocumentShare.document_id == doc_id,
        DocumentShare.shared_with_user_id == user.id
    ).first()

    if not share:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this document")

    if require_download and share.permission != "DOWNLOAD":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You only have VIEW metadata permission; DOWNLOAD permission is required"
        )

    return doc

def download_and_decrypt_document(db: Session, doc_id: int, user: User) -> tuple[Document, bytes]:
    doc = get_authorized_document(db, doc_id, user, require_download=True)
    file_path = get_encrypted_file_path(doc.storage_key)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encrypted file missing from storage")

    with open(file_path, "rb") as f:
        ciphertext = f.read()

    plaintext = EncryptionService.decrypt_bytes(ciphertext, doc.nonce_hex, doc.encryption_version)

    try:
        record_audit_log(
            db=db,
            user_id=user.id,
            action="DOWNLOAD",
            document_id=doc.id,
            details=f"Authorized download of '{doc.original_filename}'"
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return doc, plaintext

def share_document_service(db: Session, doc_id: int, owner: User, target_email: str, permission: str) -> dict:
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if doc.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the document owner can share access")

    if target_email.lower() == owner.email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share document with yourself")

    target_user = db.query(User).filter(User.email == target_email.lower()).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user email is not registered")

    try:
        existing_share = db.query(DocumentShare).filter(
            DocumentShare.document_id == doc_id,
            DocumentShare.shared_with_user_id == target_user.id
        ).first()

        if existing_share:
            existing_share.permission = permission
            share_obj = existing_share
        else:
            share_obj = DocumentShare(
                document_id=doc_id,
                shared_with_user_id=target_user.id,
                permission=permission
            )
            db.add(share_obj)

        record_audit_log(
            db=db,
            user_id=owner.id,
            action="SHARE",
            document_id=doc.id,
            details=f"Shared '{doc.original_filename}' with {target_user.email} ({permission})"
        )
        db.commit()
        db.refresh(share_obj)
        return {
            "id": share_obj.id,
            "document_id": share_obj.document_id,
            "shared_with_user_id": share_obj.shared_with_user_id,
            "shared_with_email": target_user.email,
            "permission": share_obj.permission,
            "created_at": share_obj.created_at
        }
    except Exception:
        db.rollback()
        raise

def revoke_share_service(db: Session, doc_id: int, owner: User, target_user_id: int):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if doc.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the document owner can revoke access")

    share = db.query(DocumentShare).filter(
        DocumentShare.document_id == doc_id,
        DocumentShare.shared_with_user_id == target_user_id
    ).first()

    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share permission record not found")

    target_email = share.shared_user.email if share.shared_user else f"user_id={target_user_id}"

    try:
        db.delete(share)
        record_audit_log(
            db=db,
            user_id=owner.id,
            action="REVOKE",
            document_id=doc.id,
            details=f"Revoked access to '{doc.original_filename}' from {target_email}"
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

def delete_document_service(db: Session, doc_id: int, owner: User):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if doc.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the document owner can delete this file")

    file_path = get_encrypted_file_path(doc.storage_key)
    filename = doc.original_filename

    try:
        db.delete(doc)
        record_audit_log(
            db=db,
            user_id=owner.id,
            action="DELETE",
            document_id=doc_id,
            details=f"Deleted document '{filename}'"
        )
        db.commit()
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        db.rollback()
        raise
