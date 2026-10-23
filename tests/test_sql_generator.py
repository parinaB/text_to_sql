"""Unit tests for SQL generation module and structured response parsing."""

import json
import pytest
from database import init_database
from schema_inspector import inspect_database
from retriever import retrieve_context
from sql_generator import (
    SQLGenerator,
    GeneratedSQLResponse,
    DeterministicTestLLMClient,
    OllamaLLMClient,
    LLMServiceUnavailableError,
    MalformedLLMResponseError,
    parse_and_validate_llm_response,
)


def test_parse_valid_json():
    """Verify clean JSON parses into GeneratedSQLResponse."""
    raw = json.dumps({
        "sql": "SELECT COUNT(*) FROM orders;",
        "parameters": {"min_amount": 100},
        "assumptions": ["Completed orders only"],
        "explanation": "Calculates order count",
        "is_supported": True,
    })
    resp = parse_and_validate_llm_response(raw)
    assert isinstance(resp, GeneratedSQLResponse)
    assert resp.sql == "SELECT COUNT(*) FROM orders;"
    assert resp.parameters == {"min_amount": 100}
    assert resp.assumptions == ["Completed orders only"]
    assert resp.is_supported is True


def test_parse_markdown_wrapped_json():
    """Verify markdown code-fenced JSON is correctly extracted and parsed."""
    raw = """```json
    {
        "sql": "SELECT * FROM customers;",
        "parameters": {},
        "assumptions": [],
        "explanation": "Selects all customers",
        "is_supported": true
    }
    ```"""
    resp = parse_and_validate_llm_response(raw)
    assert resp.sql == "SELECT * FROM customers;"
    assert resp.is_supported is True


def test_parse_malformed_json_raises_error():
    """Verify invalid JSON raises MalformedLLMResponseError."""
    with pytest.raises(MalformedLLMResponseError):
        parse_and_validate_llm_response("This is not JSON at all: SELECT * FROM orders;")


def test_generator_with_supported_question(temp_db_path):
    """Verify SQL generator produces structured response for valid question."""
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)
    ctx = retrieve_context("How many orders did we receive in October 2026?")

    generator = SQLGenerator(client=DeterministicTestLLMClient())
    resp = generator.generate_sql(
        question="How many orders did we receive in October 2026?",
        schema=schema,
        retrieved_context=ctx,
    )

    assert isinstance(resp, GeneratedSQLResponse)
    assert resp.is_supported is True
    assert "SELECT COUNT(*)" in resp.sql
    assert "orders" in resp.sql.lower()
    assert len(resp.assumptions) > 0
    assert len(resp.explanation) > 0


def test_generator_with_unsupported_question(temp_db_path):
    """Verify generator cleanly handles unsupported questions without inventing tables or SQL."""
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)
    ctx = retrieve_context("What was our customer satisfaction CSAT score?")

    generator = SQLGenerator(client=DeterministicTestLLMClient())
    resp = generator.generate_sql(
        question="What was our customer satisfaction CSAT score?",
        schema=schema,
        retrieved_context=ctx,
    )

    assert isinstance(resp, GeneratedSQLResponse)
    assert resp.is_supported is False
    assert resp.sql == ""
    assert "schema" in resp.explanation.lower() or "does not contain" in resp.explanation.lower()


def test_generator_error_feedback_retry(temp_db_path):
    """Verify generator receives error feedback on retry and produces corrected response."""
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)
    ctx = retrieve_context("Orders count")

    generator = SQLGenerator(client=DeterministicTestLLMClient())
    resp = generator.generate_sql(
        question="Orders count",
        schema=schema,
        retrieved_context=ctx,
        error_feedback="Column 'order_cnt' does not exist in table 'orders'",
    )

    assert isinstance(resp, GeneratedSQLResponse)
    assert "Self-corrected after error diagnostic" in resp.assumptions


def test_ollama_client_unreachable_error():
    """Verify Ollama client raises LLMServiceUnavailableError when server is offline."""
    client = OllamaLLMClient(base_url="http://127.0.0.1:54321", model_name="qwen2.5-coder:7b")
    with pytest.raises(LLMServiceUnavailableError) as exc_info:
        client.generate(system_prompt="Test", user_prompt="Test")

    assert "Could not connect to Ollama" in str(exc_info.value)
    assert "ollama.com" in str(exc_info.value)
