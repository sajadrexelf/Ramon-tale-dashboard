from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "production", "staging", "test"]


def _resolve_env_files() -> tuple[str, ...]:
    env = os.getenv("ECONCONTENT_ENVIRONMENT", "development").lower()
    if env in {"prod", "production"}:
        return (".env", ".env.prod")
    if env in {"dev", "development"}:
        return (".env", ".env.dev")
    if env in {"test", "testing"}:
        return (".env", ".env.test")
    return (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ECONCONTENT_",
        env_file=_resolve_env_files(),
        env_nested_delimiter="__",
        env_delimiter=",",
        extra="ignore",
    )

    environment: Environment = "development"
    project_name: str = "EconContent AI Assistant"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False
    rate_limit: str = "60/minute"
    allowed_hosts: list[str] = ["*"]
    cors_origins: list[str] = []
    enable_docs: bool = True
    output_path: str = "data/output.jsonl"

    database_url: str | None = None
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "econcontent"

    @property
    def async_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            "postgresql+asyncpg://"
            f"{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
