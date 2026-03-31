from __future__ import annotations

from runtime_env import configure_runtime_env

configure_runtime_env()

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Runtime
    app_env: str = "development"
    cors_allowed_origins: str = "http://localhost:8080,http://127.0.0.1:8080"

    # Database
    database_url: str = "postgresql+asyncpg://nume:nume@localhost:5432/nume"
    database_migration_url: str = ""
    database_pool_mode: Literal["auto", "pooled", "transaction", "null"] = "auto"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout_seconds: int = 30
    database_pool_recycle_seconds: int = 1800
    database_statement_cache_size: int = 100
    database_command_timeout_seconds: int = 60

    # Clerk
    clerk_secret_key: str = ""
    clerk_jwt_key: str = ""
    clerk_frontend_api_url: str = ""
    clerk_jwks_url: str = ""
    clerk_authorized_parties: str = ""

    # Azure OpenAI / OpenAI-compatible endpoint
    azure_openai_api_key: str = ""
    azure_api_key: str = ""
    openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_base_url: str = ""
    openai_base_url: str = ""
    azure_openai_api_version: str = ""
    openai_api_version: str = ""
    azure_openai_deployment: str = ""
    azure_openai_deployment_name: str = ""
    azure_openai_model: str = ""
    openai_model: str = ""

    # Garmin
    garmin_enabled: bool = False
    garmin_username: str = ""
    garmin_password: str = ""
    garmin_token_dir: str = "./garmin_tokens"
    garmin_sync_interval_min: int = 45
    garmin_sync_days_back: int = 30

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def migration_database_url(self) -> str:
        return self.database_migration_url.strip() or self.database_url


settings = Settings()
