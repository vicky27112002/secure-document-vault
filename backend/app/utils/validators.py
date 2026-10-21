import os
from fastapi import UploadFile, HTTPException, status
from app.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}

def validate_upload_file(file: UploadFile, content: bytes):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is missing")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: PDF, DOCX, PNG, JPG"
        )

    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME type '{file.content_type}'"
        )

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB} MB"
        )

    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot upload an empty file")

    # Verify magic bytes to prevent simple extension spoofing
    if ext == ".pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF file content")
    if ext == ".png" and not content.startswith(b"\x89PNG"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PNG file content")
    if ext in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JPEG file content")
    if ext == ".docx" and not content.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid DOCX file content")
