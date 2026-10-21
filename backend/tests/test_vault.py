import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.config import settings
from app.models import AuditLog, DocumentShare
from app.services import document_service

# Setup isolated test database & temporary encrypted file storage
TEST_STORAGE = tempfile.mkdtemp()
settings.STORAGE_DIR = TEST_STORAGE

SQLALCHEMY_TEST_URL = "sqlite:///./test_vault.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def teardown_module(module):
    if os.path.exists("./test_vault.db"):
        os.remove("./test_vault.db")
    shutil.rmtree(TEST_STORAGE, ignore_errors=True)

def register_and_login(email: str, name: str = "Test User", password: str = "Secret123"):
    client.post("/auth/register", json={"email": email, "full_name": name, "password": password})
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.json()

# 1. Test Registration, Login & Token Refresh
def test_01_auth_and_refresh_flow():
    tokens = register_and_login("alice@example.com")
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    refresh_res = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()

# 2. Test Encrypted File Upload & Verify Ciphertext on Disk
def test_02_upload_encrypts_file_on_disk():
    tokens = register_and_login("owner@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    pdf_bytes = b"%PDF-1.4 Confidential Financial Report 2026"

    res = client.post(
        "/documents",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        headers=headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["original_filename"] == "report.pdf"
    assert data["encryption_version"] == "v1_aes_256_gcm"
    assert "storage_key" not in data  # Internal storage key must never be exposed

    # Inspect stored file on disk to prove it is encrypted and not plaintext
    enc_files = os.listdir(TEST_STORAGE)
    assert len(enc_files) == 1
    with open(os.path.join(TEST_STORAGE, enc_files[0]), "rb") as f:
        disk_bytes = f.read()
    assert pdf_bytes not in disk_bytes

# 3. Test Authorized Download & Decryption
def test_03_authorized_download_decrypts_accurately():
    tokens = register_and_login("owner@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    pdf_bytes = b"%PDF-1.4 Exact Decryption Verification Payload"

    up = client.post("/documents", files={"file": ("doc.pdf", pdf_bytes, "application/pdf")}, headers=headers)
    doc_id = up.json()["id"]

    dl = client.get(f"/documents/{doc_id}/download", headers=headers)
    assert dl.status_code == 200
    assert dl.content == pdf_bytes

# 4. Test Reject Invalid File Extension / MIME Type
def test_04_reject_unsupported_file_type():
    tokens = register_and_login("owner@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    res = client.post(
        "/documents",
        files={"file": ("malware.exe", b"MZ-binary", "application/x-msdownload")},
        headers=headers
    )
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]

# 5. Test Reject File Exceeding Max Size
def test_05_reject_oversized_file():
    tokens = register_and_login("owner@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    settings.MAX_FILE_SIZE_MB = 1
    large_pdf = b"%PDF-" + (b"A" * (1024 * 1024 + 500))

    res = client.post(
        "/documents",
        files={"file": ("huge.pdf", large_pdf, "application/pdf")},
        headers=headers
    )
    settings.MAX_FILE_SIZE_MB = 10
    assert res.status_code == 413

# 6. Test Unauthorized User Cannot Access or Download Document
def test_06_unauthorized_user_blocked():
    owner_tokens = register_and_login("owner@example.com")
    hacker_tokens = register_and_login("intruder@example.com")

    up = client.post(
        "/documents",
        files={"file": ("secret.pdf", b"%PDF-1.4 secret", "application/pdf")},
        headers={"Authorization": f"Bearer {owner_tokens['access_token']}"}
    )
    doc_id = up.json()["id"]

    dl = client.get(
        f"/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {hacker_tokens['access_token']}"}
    )
    assert dl.status_code == 403

# 7. Test Share Document With VIEW vs DOWNLOAD Permissions
def test_07_share_permissions_enforced():
    owner_tokens = register_and_login("owner@example.com")
    viewer_tokens = register_and_login("viewer@example.com")
    owner_hdr = {"Authorization": f"Bearer {owner_tokens['access_token']}"}
    viewer_hdr = {"Authorization": f"Bearer {viewer_tokens['access_token']}"}

    up = client.post("/documents", files={"file": ("shared.pdf", b"%PDF-1.4 shared", "application/pdf")}, headers=owner_hdr)
    doc_id = up.json()["id"]

    # Grant VIEW-only permission
    sh = client.post(f"/documents/{doc_id}/share", json={"user_email": "viewer@example.com", "permission": "VIEW"}, headers=owner_hdr)
    assert sh.status_code == 200

    # Viewer can read metadata
    meta = client.get(f"/documents/{doc_id}", headers=viewer_hdr)
    assert meta.status_code == 200

    # Viewer cannot download with VIEW permission
    dl_fail = client.get(f"/documents/{doc_id}/download", headers=viewer_hdr)
    assert dl_fail.status_code == 403

    # Upgrade to DOWNLOAD permission
    client.post(f"/documents/{doc_id}/share", json={"user_email": "viewer@example.com", "permission": "DOWNLOAD"}, headers=owner_hdr)
    dl_ok = client.get(f"/documents/{doc_id}/download", headers=viewer_hdr)
    assert dl_ok.status_code == 200
    assert dl_ok.content == b"%PDF-1.4 shared"

# 8. Test Revoke Access Blocks Subsequent Downloads Immediately
def test_08_revoke_access_blocks_user():
    owner_tokens = register_and_login("owner@example.com")
    bob_tokens = register_and_login("bob@example.com")
    owner_hdr = {"Authorization": f"Bearer {owner_tokens['access_token']}"}
    bob_hdr = {"Authorization": f"Bearer {bob_tokens['access_token']}"}

    up = client.post("/documents", files={"file": ("revoke.pdf", b"%PDF-1.4 data", "application/pdf")}, headers=owner_hdr)
    doc_id = up.json()["id"]

    sh = client.post(f"/documents/{doc_id}/share", json={"user_email": "bob@example.com", "permission": "DOWNLOAD"}, headers=owner_hdr)
    bob_id = sh.json()["shared_with_user_id"]

    del_res = client.delete(f"/documents/{doc_id}/share/{bob_id}", headers=owner_hdr)
    assert del_res.status_code == 204

    dl_after = client.get(f"/documents/{doc_id}/download", headers=bob_hdr)
    assert dl_after.status_code == 403

# 9. Test Corrupted Ciphertext Triggers AES-GCM Authentication Tag Failure
def test_09_corrupted_ciphertext_detected():
    tokens = register_and_login("owner@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    up = client.post("/documents", files={"file": ("tamper.pdf", b"%PDF-1.4 original", "application/pdf")}, headers=headers)
    doc_id = up.json()["id"]

    # Tamper with the encrypted file on disk
    enc_file = os.listdir(TEST_STORAGE)[0]
    enc_path = os.path.join(TEST_STORAGE, enc_file)
    with open(enc_path, "wb") as f:
        f.write(b"corrupted_ciphertext_bytes_0123456789")

    dl = client.get(f"/documents/{doc_id}/download", headers=headers)
    assert dl.status_code == 500
    assert "integrity check failed" in dl.json()["detail"].lower()

# 10. Test Atomic Transaction Rollback When Audit Log Fails During Share
def test_10_atomic_share_and_audit_rollback(monkeypatch):
    owner_tokens = register_and_login("owner@example.com")
    register_and_login("partner@example.com")
    owner_hdr = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

    up = client.post("/documents", files={"file": ("atomic.pdf", b"%PDF-1.4 atomic", "application/pdf")}, headers=owner_hdr)
    doc_id = up.json()["id"]

    def broken_audit_log(*args, **kwargs):
        raise RuntimeError("Simulated database failure during audit logging")

    monkeypatch.setattr(document_service, "record_audit_log", broken_audit_log)

    with pytest.raises(RuntimeError):
        client.post(
            f"/documents/{doc_id}/share",
            json={"user_email": "partner@example.com", "permission": "DOWNLOAD"},
            headers=owner_hdr
        )

    # Verify the DocumentShare row was rolled back and NOT persisted
    db = TestingSessionLocal()
    shares = db.query(DocumentShare).filter(DocumentShare.document_id == doc_id).all()
    db.close()
    assert len(shares) == 0

# 11. Test Audit Log Filtering & Pagination
def test_11_audit_logs_recorded_and_filterable():
    tokens = register_and_login("auditor@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    client.post("/documents", files={"file": ("logtest.pdf", b"%PDF-1.4 log", "application/pdf")}, headers=headers)

    logs_res = client.get("/audit-logs?action=UPLOAD", headers=headers)
    assert logs_res.status_code == 200
    data = logs_res.json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "UPLOAD"
