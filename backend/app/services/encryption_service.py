import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from fastapi import HTTPException, status
from app.config import settings

class EncryptionService:
    CURRENT_VERSION = "v1_aes_256_gcm"

    @staticmethod
    def _get_master_key() -> bytes:
        key_hex = settings.MASTER_ENCRYPTION_KEY
        try:
            key_bytes = bytes.fromhex(key_hex)
            if len(key_bytes) != 32:
                raise ValueError("Master key must be exactly 32 bytes (64 hex chars)")
            return key_bytes
        except ValueError:
            # Fallback deterministic 32-byte key derivation if non-hex string is provided
            return key_hex.encode("utf-8").ljust(32, b"0")[:32]

    @classmethod
    def encrypt_bytes(cls, plaintext: bytes) -> tuple[bytes, str, str]:
        """
        Encrypts plaintext using AES-256-GCM.
        Returns (ciphertext_with_auth_tag, nonce_hex, encryption_version).
        """
        key = cls._get_master_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12) # 96-bit standard NIST nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return ciphertext, nonce.hex(), cls.CURRENT_VERSION

    @classmethod
    def decrypt_bytes(cls, ciphertext: bytes, nonce_hex: str, version: str) -> bytes:
        """
        Verifies authentication tag and decrypts AES-256-GCM ciphertext.
        Raises 500 Integrity Error if ciphertext or tag is tampered/corrupted.
        """
        if version != cls.CURRENT_VERSION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported encryption version: {version}"
            )
        key = cls._get_master_key()
        aesgcm = AESGCM(key)
        try:
            nonce = bytes.fromhex(nonce_hex)
            return aesgcm.decrypt(nonce, ciphertext, None)
        except (InvalidTag, ValueError):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Document integrity check failed: Ciphertext is corrupted or tampered with."
            )
