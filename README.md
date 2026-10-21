# Secure Document Vault

A full-stack document-management application built with **React,
FastAPI, PostgreSQL, and SQLAlchemy**. It lets registered users upload
supported files, stores the file contents encrypted using
**AES-256-GCM**, controls access to document metadata and downloads,
supports sharing with explicit permissions, and records important
actions in an audit log.

> **Project status:** This README documents the code and configuration
> included in this repository. It is a learning/portfolio project, not a
> security certification or a claim of production readiness.

## Features

### Authentication

-   User registration and login.
-   Password hashing with `bcrypt`.
-   JWT access and refresh tokens.
-   Authenticated endpoint for retrieving the current user.
-   Frontend token handling and an automatic refresh attempt after
    eligible `401` responses.

### Document management

-   Upload support for PDF, DOCX, PNG, JPG, and JPEG files.
-   Backend checks for filename, extension, declared MIME type, size
    limit, non-empty content, and basic file-signature bytes.
-   Encrypts uploaded bytes before writing the file to persistent
    storage.
-   Stores document metadata in PostgreSQL and encrypted content as
    `.enc` files.
-   Authorized metadata viewing and download/decryption.
-   Search, MIME-type/date filtering, and pagination for document
    listings.
-   Delete documents.

### Sharing and access control

-   Share a document with another registered user.
-   Grant either `VIEW` or `DOWNLOAD` permission.
-   Only the owner can share or revoke access.
-   A `VIEW` share permits metadata access but not download.
-   Revoke a share to remove the recipient's access.

### Audit trail

-   Records important actions such as `LOGIN`, `UPLOAD`, `DOWNLOAD`,
    `SHARE`, `REVOKE`, and `DELETE` where implemented.
-   Supports filtering by action, user, document, and date range, plus
    pagination.
-   Audit records are added to the caller's SQLAlchemy session so
    related changes can be committed together where the service uses
    that transaction.

## Technology stack

  Area                       Technology
  -------------------------- -----------------------------------
  Frontend                   React 18, Vite, React Router
  HTTP client                Axios
  Backend API                FastAPI
  Data validation/settings   Pydantic, Pydantic Settings
  Database                   PostgreSQL
  ORM                        SQLAlchemy
  Database driver            psycopg
  Authentication             JWT (`python-jose`)
  Password hashing           bcrypt
  File encryption            `cryptography` library, AES-GCM
  Tests                      pytest, FastAPI TestClient, httpx
  Container configuration    Dockerfiles and Docker Compose

## Architecture

``` text
Browser
  |
  | React + Vite (http://localhost:5173)
  | Axios attaches access token
  v
FastAPI API (http://localhost:8000)
  |
  +-- /auth       Registration, login, refresh, current user
  +-- /documents  Upload, list, metadata, download, share, revoke, delete
  +-- /audit-logs Filtered audit history
  |
  +-- SQLAlchemy --> PostgreSQL
  |                  Users, documents, shares, audit records
  |
  +-- EncryptionService --> AES-256-GCM
  |                          |
  |                          v
  |                     backend/storage/*.enc
  |
  +-- Security utilities --> bcrypt password hashes and JWT validation
```

The database stores document metadata and references to encrypted files.
The encrypted file itself is stored separately in the configured storage
directory. The API does not return the internal storage key as document
metadata.

## Repository structure

``` text
secure_document_vault/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   └── audit_logs.py
│   │   ├── services/
│   │   │   ├── audit_service.py
│   │   │   ├── document_service.py
│   │   │   └── encryption_service.py
│   │   ├── utils/
│   │   │   ├── security.py
│   │   │   └── validators.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── tests/
│   │   └── test_vault.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── api.js
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── Dockerfile
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Prerequisites

For running locally without Docker:

-   Python 3.11 recommended (the backend Dockerfile uses Python 3.11).
-   Node.js 20 recommended (the frontend Dockerfile uses Node 20).
-   PostgreSQL running locally.
-   Git (optional, for cloning/version control).

## Configuration and secrets

The backend reads settings from environment variables and a `.env` file
in its working directory. The repository includes a root `.env.example`
as a template.

1.  Create the PostgreSQL database named `document_db` using your
    PostgreSQL administration tool or SQL shell.

2.  In PowerShell, from the project root, copy the template into the
    backend directory:

    ``` powershell
    Copy-Item .env.example backend/.env
    ```

3.  Edit `backend/.env` and set the actual database connection string
    for your local PostgreSQL user and database.

4.  Generate **separate, random** values for `JWT_SECRET_KEY` and
    `MASTER_ENCRYPTION_KEY`; do not use the example values. The
    encryption key must be exactly 32 bytes (64 hexadecimal characters)
    for AES-256-GCM.

For example, generate a random hexadecimal value with Python:

``` powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Run the command separately for each secret and paste the results into
the corresponding variables. Do not commit `backend/.env`, real
credentials, secret keys, or actual documents.

**Important security note:** The reviewed `backend/app/config.py`
currently contains fallback defaults for the database URL and secret
values. Before publishing or deploying the project, remove unsafe
hardcoded secret defaults and require strong values from the
environment. The `.env.example` should contain placeholders only. If
real secrets have ever been committed or exposed, rotate them. Changing
the encryption key makes previously encrypted documents unreadable
unless they are decrypted/re-encrypted or the old key remains securely
available.

The configurable file limit defaults to 10 MB. `STORAGE_DIR` controls
where encrypted files are written; the default is `./storage`, resolved
relative to the backend process's working directory.

## Run locally (without Docker)

### 1. Start PostgreSQL

Start your local PostgreSQL service and make sure the `document_db`
database exists. Configure `DATABASE_URL` in `backend/.env` to match
your PostgreSQL username, password, host, port, and database.

### 2. Start the backend

Open a terminal in the project root and run:

``` powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation, you can use the virtual environment's
interpreter directly instead of changing execution-policy settings:

``` powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

The backend creates the SQLAlchemy tables at application startup. For
production use, prefer a migration tool and an explicit migration
workflow.

-   API base: `http://127.0.0.1:8000`
-   Interactive Swagger docs: `http://127.0.0.1:8000/docs`
-   ReDoc: `http://127.0.0.1:8000/redoc`
-   Health check: `http://127.0.0.1:8000/health`

### 3. Start the frontend

Open a second terminal:

``` powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The frontend defaults to `http://localhost:8000` for the API. To use a
different API address, set `VITE_API_URL` in the frontend environment
before starting/building the app. The backend CORS configuration
currently allows the local Vite origins `http://localhost:5173` and
`http://127.0.0.1:5173`.

### 4. Use the application

1.  Register a user.
2.  Log in.
3.  Upload a supported file.
4.  View and filter documents.
5.  Open document details and share with another registered user's email
    using `VIEW` or `DOWNLOAD`.
6.  Test that `VIEW` access does not allow downloading.
7.  Revoke a share and verify the recipient can no longer access the
    document.
8.  Review audit logs.

## API reference

FastAPI's `/docs` endpoint is the authoritative, interactive reference
for request schemas and response models.

  -----------------------------------------------------------------------------------
  Method                  Endpoint                            Purpose
  ----------------------- ----------------------------------- -----------------------
  `GET`                   `/health`                           Health check

  `POST`                  `/auth/register`                    Register a user

  `POST`                  `/auth/login`                       Authenticate and issue
                                                              tokens

  `POST`                  `/auth/refresh`                     Exchange a valid
                                                              refresh token for new
                                                              tokens

  `GET`                   `/auth/me`                          Return the
                                                              authenticated user

  `POST`                  `/documents`                        Upload and encrypt a
                                                              file (multipart form
                                                              field: `file`)

  `GET`                   `/documents`                        List accessible
                                                              documents; supports
                                                              search, MIME/date
                                                              filters, and pagination

  `GET`                   `/documents/{id}`                   Get document metadata
                                                              if authorized

  `GET`                   `/documents/{id}/download`          Authorize, decrypt, and
                                                              download the file

  `POST`                  `/documents/{id}/share`             Share with a registered
                                                              user's email and
                                                              permission

  `DELETE`                `/documents/{id}/share/{user_id}`   Revoke that user's
                                                              share

  `DELETE`                `/documents/{id}`                   Delete a document

  `GET`                   `/audit-logs`                       Retrieve filtered and
                                                              paginated audit logs
  -----------------------------------------------------------------------------------

Common query parameters include `page` and `size`; document listing also
supports `search`, `mime_type`, `start_date`, and `end_date`. Audit logs
support `action`, `user_id`, `document_id`, `start_date`, and
`end_date`.

### Authentication example

For protected endpoints, send the access token in the HTTP header:

``` http
Authorization: Bearer <access_token>
```

The login endpoint returns `access_token`, `refresh_token`, and
`token_type`. The frontend stores tokens in `localStorage` and attempts
a refresh after an eligible unauthorized response.

## Encryption and security design

-   Uploaded bytes are encrypted with the Python `cryptography`
    library's AES-GCM implementation using a 256-bit key and a random
    12-byte nonce.
-   AES-GCM provides confidentiality and authentication/integrity
    checking; tampered ciphertext fails decryption.
-   The encryption version is stored as metadata (`v1_aes_256_gcm`) to
    identify the current format.
-   Passwords are stored as bcrypt hashes, not as plaintext.
-   JWT access and refresh tokens carry different token types and expiry
    times.
-   Document access is checked before metadata is returned or a file is
    decrypted for download.
-   Internal storage filenames use generated identifiers and are not
    exposed through the document response.
-   File validation checks the extension, MIME type, configured size
    limit, non-empty content, and basic magic bytes.

This is a project-level security implementation, not a substitute for a
professional security review. For production, also consider rate
limiting, secure token storage (rather than browser `localStorage` where
appropriate), refresh-token revocation/rotation, HTTPS, stronger upload
streaming/size enforcement before buffering, robust content scanning,
key management outside the application environment, authorization and
concurrency tests, and operational monitoring.

## Database entities

The SQLAlchemy models define these main entities:

-   **User** --- email, full name, password hash, and creation
    timestamp.
-   **Document** --- owner, original filename, MIME type, file size,
    storage key, encryption version, nonce, and creation timestamp.
-   **DocumentShare** --- document, recipient user, permission (`VIEW`
    or `DOWNLOAD`), and creation timestamp.
-   **AuditLog** --- actor, action, optional document reference,
    details, and timestamp.

Relationships connect users to owned documents and documents to share
records. Audit records can refer to users and documents.

## Tests

The backend test suite is in `backend/tests/test_vault.py`. It uses
FastAPI's `TestClient`, a separate SQLite test database, and temporary
file storage for isolation.

Run the tests from the backend directory:

``` powershell
cd backend
python -m pytest tests/test_vault.py -v
```

The tests cover authentication/token refresh, encrypted storage and
download, file validation and size limits, access restrictions, share
permissions, revocation, deletion, and audit-related behavior. The test
file should be treated as the definitive list of implemented cases; not
every possible security or failure scenario is covered.

## Docker

Dockerfiles are included for the backend and frontend, and a
`docker-compose.yml` is present.

**Current Compose configuration starts only the backend and frontend
services. It does not define a PostgreSQL container.** It expects the
backend environment file at `backend/.env`, and the configured database
must be reachable from the backend container. A `DATABASE_URL` using
`localhost` inside a container will refer to that container itself, not
to PostgreSQL running on the Windows host. The connection string must be
adjusted for the chosen database topology.

After Docker is installed and the environment is configured
appropriately, the current configuration can be started from the project
root with:

``` powershell
docker compose up --build
```

-   Frontend: `http://localhost:5173`
-   Backend: `http://localhost:8000`
-   API docs: `http://localhost:8000/docs`

Because the Compose file does not include PostgreSQL and container
networking needs to be configured correctly, this command alone will not
provide a complete self-contained stack unless a reachable PostgreSQL
instance is already available. Review and update the Compose
configuration before relying on it.

## Known limitations and production considerations

-   The application is intended for learning and demonstration; it has
    not been independently security-audited.
-   The configuration currently includes hardcoded fallback secrets and
    a database URL; these must be removed before public release or
    deployment.
-   The sample `.env.example` must use placeholders and a correctly
    sized 64-character hexadecimal encryption key.
-   The current Docker Compose file does not start a database service.
-   The access/refresh token flow does not provide server-side
    refresh-token revocation.
-   File size validation occurs after the upload bytes are read into
    memory; enforce limits at the request/proxy layer or stream uploads
    for larger workloads.
-   SQLAlchemy `create_all` is used on startup instead of schema
    migrations.
-   Tests cover selected scenarios but are not a complete security test
    suite.
-   Production deployment requires HTTPS, robust secret/key management,
    backups, monitoring, operational controls, and a security review.

## License

No license file was included in the reviewed project. Add a license if
you intend to permit others to reuse, modify, or distribute the code.
