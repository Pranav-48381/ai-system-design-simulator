"""System Design Interview Simulator - Application Configuration.

Loads environment variables using Pydantic Settings v2, validating database connections,
LLM provider credentials, session limits, and real-time WebSocket parameters.
"""

from functools import lru_cache
from typing import Annotated, Any, Literal

from pydantic import (
    Field,
    PostgresDsn,
    ValidationInfo,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    InterviewerPersona,
    LLMProvider,
)


class Settings(BaseSettings):
    """Application-wide settings validated from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --------------------------------------------------------------------------
    # Application Environment & Server Settings
    # --------------------------------------------------------------------------
    APP_NAME: str = "AI System Design Interview Simulator"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str = "dev-insecure-secret-key-replace-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOWED_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
    ]

    @field_validator("ALLOWED_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """Convert JSON array or comma-delimited string to a list of origins."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(item) for item in v]
        return []

    # --------------------------------------------------------------------------
    # PostgreSQL Database Configuration
    # --------------------------------------------------------------------------
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "system_design_interview"
    DATABASE_URL: str | None = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any, info: ValidationInfo) -> str:
        """Construct postgresql+asyncpg URL if DATABASE_URL is not explicitly specified."""
        if isinstance(v, str) and v.strip():
            return v.strip()
        data = info.data
        user = data.get("POSTGRES_USER", "postgres")
        password = data.get("POSTGRES_PASSWORD", "postgres")
        server = data.get("POSTGRES_SERVER", "localhost")
        port = data.get("POSTGRES_PORT", 5432)
        db = data.get("POSTGRES_DB", "system_design_interview")
        return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

    # --------------------------------------------------------------------------
    # LLM Provider Configuration
    # --------------------------------------------------------------------------
    DEFAULT_LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI

    # OpenAI Settings
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o"

    # Anthropic Settings
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20240620"

    # Google Gemini Settings
    GOOGLE_API_KEY: str | None = None
    GOOGLE_MODEL: str = "gemini-1.5-pro"

    # Shared LLM Parameters
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 2048
    LLM_REQUEST_TIMEOUT_SECONDS: int = 60

    # --------------------------------------------------------------------------
    # LangGraph Workflow & Interview Session Settings
    # --------------------------------------------------------------------------
    LANGGRAPH_CHECKPOINTER: Literal["memory", "postgres"] = "memory"
    DEFAULT_INTERVIEWER_PERSONA: InterviewerPersona = (
        InterviewerPersona.COLLABORATIVE
    )
    MAX_TURNS_PER_STAGE: int = 8
    MAX_TOTAL_INTERVIEW_TURNS: int = 40
    STAGE_TIME_LIMIT_MINUTES: int = 10

    # --------------------------------------------------------------------------
    # WebSocket Streaming & Real-Time Connection
    # --------------------------------------------------------------------------
    WS_HEARTBEAT_INTERVAL_SECONDS: int = 30
    WS_MESSAGE_RATE_LIMIT_PER_MINUTE: int = 60
    STREAMING_CHUNK_DELAY_MS: int = 0

    @property
    def is_production(self) -> bool:
        """Check whether the application is running in production mode."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check whether the application is running in development mode."""
        return self.APP_ENV == "development"

    @property
    def is_test(self) -> bool:
        """Check whether the application is running in test mode."""
        return self.APP_ENV == "test"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()


# Default singleton instance for direct import
settings: Settings = get_settings()
