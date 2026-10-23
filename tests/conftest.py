"""Shared pytest fixtures."""

import os
import tempfile
import pytest
from pathlib import Path
from config import AppConfig, get_config


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database file path."""
    db_file = tmp_path / "test_business.db"
    return str(db_file)


@pytest.fixture
def temp_chroma_dir(tmp_path):
    """Provide a temporary ChromaDB directory path."""
    chroma_dir = tmp_path / "test_chroma"
    chroma_dir.mkdir()
    return str(chroma_dir)


@pytest.fixture
def test_config(temp_db_path, temp_chroma_dir):
    """Provide a test AppConfig instance pointing to temporary resources."""
    return AppConfig(
        llm_provider="deterministic",
        embedding_provider="deterministic",
        database_path=temp_db_path,
        chroma_persist_dir=temp_chroma_dir,
        max_retries=2,
        query_timeout_seconds=2.0,
        max_result_rows=50,
        allowed_tables={"customers", "products", "orders", "order_items"},
    )
