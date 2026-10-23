"""Configuration management for the Text-to-SQL AI Agent."""

import os
from pathlib import Path
from typing import Literal, Optional, Set, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Central application configuration with strict validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider Selections
    llm_provider: Literal["deterministic", "ollama", "openai", "gemini"] = Field(
        default="deterministic",
        description="LLM provider: 'deterministic' (for offline testing), 'ollama', 'openai', or 'gemini'",
    )
    embedding_provider: Literal["deterministic", "ollama", "openai", "gemini"] = Field(
        default="deterministic",
        description="Embedding provider: 'deterministic' (for offline testing), 'ollama', 'openai', or 'gemini'",
    )

    # Ollama Settings
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for local Ollama server",
    )
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Embedding model name for vector retrieval",
    )
    llm_model: str = Field(
        default="qwen2.5-coder:7b",
        description="LLM model name for SQL generation",
    )

    # Cloud Provider Settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="API key for OpenAI",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model identifier",
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="API key for Google Gemini",
    )
    gemini_model: str = Field(
        default="gemini-1.5-flash",
        description="Gemini model identifier",
    )

    # Storage Settings
    database_path: str = Field(
        default="business.db",
        description="Path to SQLite database file",
    )
    chroma_persist_dir: str = Field(
        default="./chroma_data",
        description="Directory for ChromaDB vector storage",
    )

    # Security & Execution Limits
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum self-healing retry attempts for SQL generation/validation",
    )
    query_timeout_seconds: float = Field(
        default=5.0,
        gt=0.0,
        le=60.0,
        description="Query execution timeout ceiling in seconds",
    )
    max_result_rows: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of rows returned by a query",
    )
    allowed_tables: Union[Set[str], str] = Field(
        default={"customers", "products", "orders", "order_items"},
        description="Set of approved table names that queries are permitted to access",
    )

    # Observability
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Application logging level",
    )

    @field_validator("allowed_tables", mode="before")
    @classmethod
    def parse_allowed_tables(cls, v: Union[Set[str], str, list]) -> Set[str]:
        if isinstance(v, str):
            parts = [t.strip().lower() for t in v.split(",") if t.strip()]
            return set(parts)
        if isinstance(v, (list, set)):
            return {str(t).strip().lower() for t in v if str(t).strip()}
        raise ValueError(f"Invalid format for allowed_tables: {v}")

    def get_resolved_db_path(self) -> Path:
        """Return absolute Path for database."""
        return Path(self.database_path).resolve()

    def get_resolved_chroma_dir(self) -> Path:
        """Return absolute Path for ChromaDB directory."""
        return Path(self.chroma_persist_dir).resolve()


_config_instance: Optional[AppConfig] = None


def get_config(force_reload: bool = False, **kwargs) -> AppConfig:
    """Retrieve the application configuration singleton."""
    global _config_instance
    if _config_instance is None or force_reload:
        _config_instance = AppConfig(**kwargs)
    return _config_instance
