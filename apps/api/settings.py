from __future__ import annotations

from runtime_env import configure_runtime_env

configure_runtime_env()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://nume:nume@localhost:5432/nume"

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


settings = Settings()
