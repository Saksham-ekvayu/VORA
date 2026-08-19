import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), ".env"), extra="ignore"
    )

    service_name: str = "vora-service"
    port: int = 8000
    database_url: str = "postgresql+asyncpg://vora:vora@localhost:5432/vora"
    # Backward-compatible alias — prefer DATABASE_URL / database_url
    mongodb_uri: str | None = None
    jwt_secret: str = "change-me"
    jwt_project_salt: str = "change-me"
    jwt_expires_in: str = "7d"
    cors_origin: str = ""
    email_user: str = ""
    email_pass: str = ""
    email_from: str = ""
    openai_api_key: str = ""
    compliance_api_base: str = ""
    compliance_model_name: str = "gpt-4o-mini"
    allowed_extensions: str = "pdf,doc,docx"
    max_file_size: float = 10.0

    # AI Configuration
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    similarity_threshold_high: float = 75.0
    similarity_threshold_medium: float = 50.0
    min_deployment_words: int = 3

    # Compliance Scoring Configuration
    compliance_score_threshold: float = 0.7
    compliance_sim_high: float = 80.0
    compliance_sim_medium: float = 60.0
    compliance_sim_low: float = 40.0
    compliance_score_high: float = 0.95
    compliance_score_medium: float = 0.75
    compliance_score_low: float = 0.60
    compliance_score_very_low: float = 0.30

    def resolved_database_url(self) -> str:
        url = self.database_url
        if not url and self.mongodb_uri and self.mongodb_uri.startswith("postgresql"):
            url = self.mongodb_uri
        if not url:
            url = "postgresql+asyncpg://vora:vora@localhost:5432/vora"
        # Ensure SQLAlchemy async driver
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        elif url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
