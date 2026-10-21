# Secure Document Vault (Intern 2 Assignment)

A full-stack encrypted document management application built with **FastAPI**, **PostgreSQL**, **SQLAlchemy**, **AES-256-GCM (cryptography)**, and **ReactJS (Vite)**.

---

## 1. Localhost Setup in Antigravity IDE

### Prerequisites
- Python 3.10+
- Node.js 18+
- Local PostgreSQL running on `localhost:5432` with database `document_db` created:
  ```sql
  CREATE DATABASE document_db;
  ```

### Backend Setup
```bash
cd secure_document_vault/backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd secure_document_vault/frontend
npm install
npm run dev
```

### Running Tests
```bash
cd secure_document_vault/backend
pytest tests/test_vault.py -v
```

---

## 2. Architecture Highlights

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend API | FastAPI 0.115 | REST endpoints with automatic OpenAPI docs |
| Database ORM | SQLAlchemy 2.0 | User, Document, DocumentShare, AuditLog models |
| Auth | JWT (python-jose) + bcrypt | Access & refresh token authentication |
| Encryption | AES-256-GCM (cryptography) | Authenticated encryption with integrity verification |
| Validation | Pydantic v2 + magic-byte checks | Extension, MIME, size, and file content validation |
| Frontend | React 18 + Vite 5 | SPA with protected routes & Axios interceptors |
| Audit Trail | Transactional logging | Every action (LOGIN, UPLOAD, DOWNLOAD, SHARE, REVOKE, DELETE) recorded |

---

## 3. API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and receive JWT tokens
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info

### Documents
- `POST /documents` - Upload & encrypt a document
- `GET /documents` - List accessible documents (with search, filter, pagination)
- `GET /documents/{id}` - Get document metadata
- `GET /documents/{id}/download` - Decrypt & download document
- `POST /documents/{id}/share` - Share document with another user
- `DELETE /documents/{id}/share/{user_id}` - Revoke share access
- `DELETE /documents/{id}` - Delete document

### Audit Logs
- `GET /audit-logs` - View filterable & paginated audit logs

---

## 4. Security Features
- **AES-256-GCM** authenticated encryption (plaintext never written to disk)
- **bcrypt** password hashing with salt
- **JWT** access + refresh token flow
- **Role-based access**: OWNER / DOWNLOAD / VIEW permissions
- **File validation**: extension, MIME type, magic bytes, 10 MB size limit
- **Tamper detection**: GCM authentication tag verifies ciphertext integrity
- **Atomic transactions**: audit logs and shares committed together or rolled back
