import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:Iliketom%4027@localhost:5432/document_db"
    JWT_SECRET_KEY: str = "super_secret_jwt_key_for_local_dev_vault_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MASTER_ENCRYPTION_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef"
    MAX_FILE_SIZE_MB: int = 10
    STORAGE_DIR: str = "./storage"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
