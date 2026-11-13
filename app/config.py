"""Central settings, read from environment / .env (owner: Core app)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    jwt_secret: str = "dev-only-insecure-secret-change-me-0123456789"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    # AES-256-GCM key, base64. Used by app/security/crypto.py
    field_encryption_key: str = ""

    # Updated specs: SQLite. One database file for the whole app.
    database_url: str = "sqlite:///./data/university.db"

    seed_demo_users: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
