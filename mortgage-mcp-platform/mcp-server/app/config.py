"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the MCP mortgage platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="mortgage-mcp-server", validation_alias="APP_NAME")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")

    database_host: str = Field(default="localhost", validation_alias="DATABASE_HOST")
    database_port: int = Field(default=5432, validation_alias="DATABASE_PORT")
    database_user: str = Field(default="postgres", validation_alias="DATABASE_USER")
    database_password: str = Field(default="postgres", validation_alias="DATABASE_PASSWORD")
    database_name: str = Field(default="mortgage", validation_alias="DATABASE_NAME")
    database_pool_size: int = Field(default=10, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, validation_alias="DATABASE_MAX_OVERFLOW")

    google_api_key: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", validation_alias="GEMINI_MODEL")
    embedding_model: str = Field(default="models/text-embedding-004", validation_alias="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=768, validation_alias="EMBEDDING_DIMENSIONS")

    chunk_size: int = Field(default=1200, validation_alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, validation_alias="CHUNK_OVERLAP")
    rag_top_k: int = Field(default=5, validation_alias="RAG_TOP_K")
    rag_similarity_threshold: float = Field(
        default=0.65,
        validation_alias="RAG_SIMILARITY_THRESHOLD",
        description="Maximum cosine distance (pgvector <=> ) for retrieved chunks; lower is stricter",
    )

    documents_path: str = Field(default="/data/documents", validation_alias="DOCUMENTS_PATH")
    skip_startup_ingest: bool = Field(default=False, validation_alias="SKIP_STARTUP_INGEST")
    run_alembic_on_startup: bool = Field(default=True, validation_alias="RUN_ALEMBIC_ON_STARTUP")

    @field_validator("rag_similarity_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("rag_similarity_threshold must be within pgvector cosine distance bounds [0, 2]")
        return v

    @property
    def database_url_async(self) -> str:
        user = quote_plus(self.database_user)
        pwd = quote_plus(self.database_password)
        return (
            f"postgresql+asyncpg://{user}:{pwd}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic; matches async target database."""
        user = quote_plus(self.database_user)
        pwd = quote_plus(self.database_password)
        return (
            f"postgresql+asyncpg://{user}:{pwd}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
