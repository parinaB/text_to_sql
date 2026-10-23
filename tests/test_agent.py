"""End-to-end integration tests for TextToSQLAgent."""

import pytest
from database import init_database, get_table_counts
from config import AppConfig
from agent import TextToSQLAgent, AgentResponse
from sql_generator import (
    SQLGenerator,
    BaseLLMClient,
    DeterministicTestLLMClient,
    LLMServiceUnavailableError,
)


@pytest.fixture
def agent_and_db(temp_db_path, temp_chroma_dir):
    init_database(temp_db_path)
    cfg = AppConfig(
        database_path=temp_db_path,
        chroma_persist_dir=temp_chroma_dir,
        max_retries=2,
    )
    agent = TextToSQLAgent(config=cfg)
    return agent, temp_db_path


def test_agent_successful_query(agent_and_db):
    agent, _ = agent_and_db
    response = agent.ask("How many orders did we receive in October 2026?")

    assert isinstance(response, AgentResponse)
    assert response.request_id.startswith("req_")
    assert response.validation_status == "PASSED"
    assert response.sql is not None
    assert "orders" in response.sql.lower()
    assert response.execution_result is not None
    assert response.execution_result.success is True
    assert response.execution_result.rows[0]["total_orders"] == 8
    assert "Result: 8." in response.answer or "8" in response.answer
    assert response.attempts == 1


def test_agent_unsupported_question(agent_and_db):
    agent, _ = agent_and_db
    response = agent.ask("What is our customer satisfaction CSAT score?")

    assert response.validation_status == "UNSUPPORTED"
    assert response.sql == ""
    assert "cannot answer" in response.answer.lower()
    assert response.execution_result is None


def test_agent_malicious_query_rejection(agent_and_db):
    agent, db_path = agent_and_db
    counts_before = get_table_counts(db_path)

    response = agent.ask("Drop all tables now")

    assert response.validation_status == "REJECTED"
    assert "violated security" in response.answer.lower() or "prohibited" in response.answer.lower()

    # Verify zero database modification
    counts_after = get_table_counts(db_path)
    assert counts_before == counts_after


def test_agent_self_healing_retry(temp_db_path, temp_chroma_dir):
    """Verify agent detects validation failure, feeds error back to generator, and succeeds on retry."""
    init_database(temp_db_path)

    # Mock LLM that fails on attempt 1 with a forbidden statement, then self-corrects on attempt 2
    class MockFlakyLLM(BaseLLMClient):
        def __init__(self):
            self.turn = 0

        def generate(self, system_prompt: str, user_prompt: str) -> str:
            self.turn += 1
            if self.turn == 1:
                return '{"sql": "DROP TABLE customers;", "parameters": {}, "assumptions": [], "explanation": "", "is_supported": true}'
            else:
                return '{"sql": "SELECT COUNT(*) AS total_orders FROM orders;", "parameters": {}, "assumptions": ["Corrected"], "explanation": "Count orders", "is_supported": true}'

    cfg = AppConfig(database_path=temp_db_path, chroma_persist_dir=temp_chroma_dir, max_retries=2)
    generator = SQLGenerator(client=MockFlakyLLM(), config=cfg)
    agent = TextToSQLAgent(config=cfg, generator=generator)

    response = agent.ask("Order count")

    assert response.validation_status == "PASSED"
    assert response.attempts == 2
    assert "Corrected" in response.assumptions
    assert response.execution_result.rows[0]["total_orders"] == 15


def test_agent_llm_service_error(temp_db_path, temp_chroma_dir):
    """Verify agent returns clean ERROR response when external LLM service is offline."""
    init_database(temp_db_path)

    class OfflineLLM(BaseLLMClient):
        def generate(self, system_prompt: str, user_prompt: str) -> str:
            raise LLMServiceUnavailableError("Could not connect to Ollama at http://localhost:11434")

    cfg = AppConfig(database_path=temp_db_path, chroma_persist_dir=temp_chroma_dir)
    generator = SQLGenerator(client=OfflineLLM(), config=cfg)
    agent = TextToSQLAgent(config=cfg, generator=generator)

    response = agent.ask("Any question")

    assert response.validation_status == "ERROR"
    assert "Could not connect to Ollama" in response.answer
    assert response.sql is None


def test_agent_empty_result(temp_db_path, temp_chroma_dir):
    """Verify agent formats zero rows accurately without fabricating answers."""
    init_database(temp_db_path)

    class EmptyResultLLM(BaseLLMClient):
        def generate(self, system_prompt: str, user_prompt: str) -> str:
            return '{"sql": "SELECT * FROM orders WHERE order_date = \'2099-01-01\';", "parameters": {}, "assumptions": ["Future date filter"], "explanation": "Future orders", "is_supported": true}'

    cfg = AppConfig(database_path=temp_db_path, chroma_persist_dir=temp_chroma_dir)
    generator = SQLGenerator(client=EmptyResultLLM(), config=cfg)
    agent = TextToSQLAgent(config=cfg, generator=generator)

    response = agent.ask("Future orders")

    assert response.validation_status == "PASSED"
    assert response.execution_result.is_empty is True
    assert response.execution_result.row_count == 0
    assert "0 matching records" in response.answer
    assert "Future date filter" in response.answer

