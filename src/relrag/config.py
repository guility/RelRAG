"""Application configuration from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/relrag",
        description="PostgreSQL connection URL",
    )

    # Keycloak OIDC
    keycloak_url: str = Field(
        default="http://localhost:8080",
        description="Keycloak server URL",
    )
    keycloak_realm: str = Field(default="relrag", description="Keycloak realm")
    keycloak_client_id: str = Field(default="relrag-api", description="Keycloak client ID")
    keycloak_client_secret: str = Field(default="", description="Keycloak client secret")

    # Embedding API (OpenAI compatible)
    embedding_api_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI-compatible embedding API URL",
    )
    embedding_api_key: str = Field(default="", description="Embedding API key")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Default embedding model name",
    )

    # Application
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment name",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
