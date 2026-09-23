"""Application configuration via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── LLM (Groq Cloud API - OpenAI Compatible) ─────────────────────────────
    groq_api_key: str = Field(default="", description="Groq API key (free at https://console.groq.com/keys)")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    model_name: str = "openai/gpt-oss-120b"
    temperature: float = 0.1
    max_tokens: int = 512
    llm_timeout: int = 30
    max_retries: int = 3

    # Backward compatibility aliases
    xai_api_key: str = Field(default="", description="Fallback API key alias")
    xai_base_url: str = "https://api.groq.com/openai/v1"

    # ── API Security ──────────────────────────────────────────────────────────
    triage_api_key: Annotated[str, Field(description="Secret key protecting triage endpoints")]

    # ── App ───────────────────────────────────────────────────────────────────
    environment: str = "development"
    log_level: str = "INFO"
    app_version: str = "1.0.0"

    # CORS — comma-separated origins or list
    allowed_origins: str | list[str] = ["http://localhost:5173", "http://localhost:3000"]
    allowed_hosts: str | list[str] = ["localhost", "127.0.0.1", "*"]

    # ── Input Limits ──────────────────────────────────────────────────────────
    max_tickets_per_batch: int = 50
    max_ticket_length: int = 2000
    max_csv_size_mb: int = 5
    rate_limit_triage: str = "30/minute"
    rate_limit_upload: str = "5/minute"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    @field_validator("allowed_origins", mode="after")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    import json
                    return json.loads(v)
                except Exception:
                    pass
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("allowed_hosts", mode="after")
    @classmethod
    def parse_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    import json
                    return json.loads(v)
                except Exception:
                    pass
            return [h.strip() for h in v.split(",") if h.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()
