from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"), ".env"),
        extra="ignore"
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
    ai_service_url: str = "http://localhost:7000"
    ai_websocket_url: str = "ws://localhost:7000"
    ai_service_timeout: float = 10.0
    compliance_agent_url: str = "http://localhost:7009"
    email_user: str = ""
    email_pass: str = ""
    email_from: str = ""
    allowed_extensions: str = "pdf,doc,docx"
    max_file_size: int = 10

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
