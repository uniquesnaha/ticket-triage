"""Application configuration via pydantic-settings (environment variables / .env)."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Hosts that must always be accepted (local dev + the in-process test client).
_BASE_HOSTS = ["localhost", "127.0.0.1", "testserver"]


def _split_csv(v: object) -> object:
    """Accept either a JSON list or a comma-separated string."""
    if isinstance(v, str):
        stripped = v.strip()
        if stripped.startswith("["):
            return json.loads(stripped)
        return [item.strip() for item in stripped.split(",") if item.strip()]
    return v


class Settings(BaseSettings):
    # ── LLM (Groq, OpenAI-compatible API) ─────────────────────────────────────
    groq_api_key: SecretStr = SecretStr("")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    model_name: str = "openai/gpt-oss-120b"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, gt=0)
    llm_timeout: float = Field(default=20.0, gt=0, description="Per-request timeout (seconds)")
    max_retries: int = Field(default=4, ge=1, le=10, description="Total LLM attempts per ticket")
    # Prompt file in app/prompts/ (without .toml); switch versions without code changes.
    triage_prompt: str = "triage"
    # "" = automatic ("low" for gpt-oss reasoning models, unset otherwise); "none" disables.
    llm_reasoning_effort: str = ""
    llm_concurrency: int = Field(default=4, ge=1, le=32, description="Parallel LLM calls per batch")
    batch_timeout: float = Field(
        default=50.0,
        gt=0,
        description="Wall-clock budget for a batch; unfinished tickets get a safe fallback. "
        "Keep below the serverless function's maxDuration.",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    environment: str = "development"
    log_level: str = "INFO"
    app_version: str = "1.0.0"

    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    allowed_hosts: Annotated[list[str], NoDecode] = list(_BASE_HOSTS)

    # ── Input limits ──────────────────────────────────────────────────────────
    max_tickets_per_batch: int = Field(default=50, ge=1)
    max_ticket_length: int = Field(default=2000, ge=1)
    max_csv_size_mb: int = Field(default=4, ge=1)  # Vercel caps bodies at 4.5 MB
    rate_limit_triage: str = "20/minute"
    rate_limit_upload: str = "6/minute"

    # ── Platform (set automatically by Vercel at runtime) ─────────────────────
    vercel: bool = False
    vercel_url: str = ""
    vercel_branch_url: str = ""
    vercel_project_production_url: str = ""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    _split_origins = field_validator("allowed_origins", mode="before")(_split_csv)
    _split_hosts = field_validator("allowed_hosts", mode="before")(_split_csv)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        return not self.is_production

    @property
    def llm_configured(self) -> bool:
        return bool(self.groq_api_key.get_secret_value())

    @property
    def effective_reasoning_effort(self) -> str | None:
        effort = self.llm_reasoning_effort.strip().lower()
        if effort == "none":
            return None
        if effort:
            return effort
        return "low" if "gpt-oss" in self.model_name else None

    @property
    def trusted_hosts(self) -> list[str]:
        """Configured hosts plus the deployment's own Vercel domains."""
        hosts = [*_BASE_HOSTS, *self.allowed_hosts]
        hosts += [
            h
            for h in (
                self.vercel_url,
                self.vercel_branch_url,
                self.vercel_project_production_url,
            )
            if h
        ]
        return list(dict.fromkeys(hosts))


@lru_cache
def get_settings() -> Settings:
    return Settings()
