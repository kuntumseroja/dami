from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    dam_env: str = "development"
    dam_model: str = "claude-opus-4-8"
    anthropic_api_key: str = ""

    # Adapter selection (hexagonal seams)
    repo_backend: Literal["memory", "postgres"] = "postgres"
    storage_backend: Literal["local", "minio"] = "minio"
    auth_mode: Literal["dev", "oidc"] = "dev"

    database_url: str = "postgresql+asyncpg://dam:dam@localhost:5432/dam_governance"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "dam-admin"
    minio_secret_key: str = "dam-secret"
    minio_bucket: str = "governance-documents"

    dam_audit_log_path: str = "./data/audit"
    local_storage_path: str = "./data/objects"
    sop_config_dir: str = "../config/sop"


@lru_cache
def get_settings() -> Settings:
    return Settings()
