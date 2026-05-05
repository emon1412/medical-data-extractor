"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Medical Data Extractor API"
    app_version: str = "1.0.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # Database — Postgres only.
    # Local dev: spin up via `docker compose up -d postgres` (see docker-compose.yml).
    # Production: Cloud SQL via Unix socket — see backend/.env.example.
    database_url: str = Field(
        default="postgresql+psycopg://hde:hde@localhost:5434/medical_data"
    )

    # Security
    api_key: str = Field(default="dev-api-key-change-me")
    require_auth: bool = Field(default=True)

    # CORS
    cors_origins: str = Field(default="*")

    # Rate limiting
    rate_limit_default: str = Field(default="30/minute")
    rate_limit_upload: str = Field(default="5/minute")

    # Uploads
    max_upload_size_mb: int = Field(default=10)
    allowed_upload_mime_types: str = Field(default="application/pdf")

    # LLM
    openai_api_key: str = Field(default="")
    # gpt-5.4 (released 2026-03-05): frontier multimodal model, accepts images up to
    # 10M pixels uncompressed, structured outputs, ideal for medical PDF OCR.
    # For lower-cost / faster extractions you can switch to "gpt-5.4-mini".
    openai_model: str = Field(default="gpt-5.4")
    # Reasoning effort for the extraction call. Patient-info extraction is essentially
    # OCR + light structuring, so "low" gives the best speed/cost without hurting
    # accuracy. Bump to "medium" for very noisy / handwritten scans.
    openai_reasoning_effort: str = Field(default="low")
    llm_timeout_seconds: int = Field(default=45)
    llm_max_retries: int = Field(default=2)

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_upload_mime_type_list(self) -> List[str]:
        return [m.strip() for m in self.allowed_upload_mime_types.split(",") if m.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
