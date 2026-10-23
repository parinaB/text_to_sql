"""Configuration unit tests."""

import pytest
from pydantic import ValidationError
from config import AppConfig, get_config


def test_default_config():
    """Verify default configuration values."""
    cfg = AppConfig()
    assert cfg.llm_provider == "deterministic"
    assert cfg.embedding_provider == "deterministic"
    assert cfg.ollama_base_url == "http://localhost:11434"
    assert cfg.max_retries == 2
    assert cfg.query_timeout_seconds == 5.0
    assert cfg.max_result_rows == 100
    assert "customers" in cfg.allowed_tables
    assert "orders" in cfg.allowed_tables
    assert "products" in cfg.allowed_tables
    assert "order_items" in cfg.allowed_tables


def test_parse_allowed_tables_string():
    """Verify allowed_tables parses comma-separated strings."""
    cfg = AppConfig(allowed_tables="users, transactions, accounts")
    assert cfg.allowed_tables == {"users", "transactions", "accounts"}


def test_invalid_provider_rejection():
    """Verify that unsupported providers are rejected by validation."""
    with pytest.raises(ValidationError):
        AppConfig(llm_provider="unsupported_provider")

    with pytest.raises(ValidationError):
        AppConfig(embedding_provider="unsupported_embedding")


def test_timeout_bounds():
    """Verify that timeout must be positive and within bounds."""
    with pytest.raises(ValidationError):
        AppConfig(query_timeout_seconds=-1.0)

    with pytest.raises(ValidationError):
        AppConfig(query_timeout_seconds=0.0)

    with pytest.raises(ValidationError):
        AppConfig(query_timeout_seconds=100.0)


def test_max_retries_bounds():
    """Verify that max_retries enforces bounds."""
    with pytest.raises(ValidationError):
        AppConfig(max_retries=-1)

    with pytest.raises(ValidationError):
        AppConfig(max_retries=10)


def test_get_config_singleton():
    """Verify get_config singleton behavior."""
    cfg1 = get_config(force_reload=True)
    cfg2 = get_config()
    assert cfg1 is cfg2
