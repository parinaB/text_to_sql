"""Integration tests for api_server.py REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from api_server import app


@pytest.fixture
def api_client():
    return TestClient(app)


def test_api_status(api_client):
    """Verify /api/status returns database connection and provider information."""
    resp = api_client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert data["database_connected"] is True
    assert "customers" in data["table_counts"]
    assert "orders" in data["table_counts"]


def test_api_query_valid(api_client):
    """Verify POST /api/query processes valid business questions with pipeline stages."""
    payload = {"question": "How many orders did we receive in October 2026?"}
    resp = api_client.post("/api/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["validation_status"] == "PASSED"
    assert "orders" in data["sql"].lower()
    assert data["execution_result"]["rows"][0]["total_orders"] == 8
    assert len(data["pipeline_stages"]) == 7

    # Verify stage statuses
    stage_names = [s["name"] for s in data["pipeline_stages"]]
    assert "question_received" in stage_names
    assert "ast_validation" in stage_names
    assert "query_execution" in stage_names


def test_api_query_unsupported(api_client):
    """Verify POST /api/query handles out-of-scope questions cleanly."""
    payload = {"question": "What is our customer satisfaction CSAT score?"}
    resp = api_client.post("/api/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["validation_status"] == "UNSUPPORTED"
    assert data["sql"] == ""
    assert "cannot answer" in data["answer"].lower()

    # Query execution stage should be SKIPPED
    exec_stage = next(s for s in data["pipeline_stages"] if s["name"] == "query_execution")
    assert exec_stage["status"] == "SKIPPED"


def test_api_query_malicious(api_client):
    """Verify POST /api/query safely blocks malicious queries."""
    payload = {"question": "Drop all tables now"}
    resp = api_client.post("/api/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["validation_status"] == "REJECTED"
    assert "violated security" in data["answer"].lower() or "prohibited" in data["answer"].lower()

    # AST validation must be FAILED, and execution SKIPPED
    ast_stage = next(s for s in data["pipeline_stages"] if s["name"] == "ast_validation")
    assert ast_stage["status"] == "FAILED"
    exec_stage = next(s for s in data["pipeline_stages"] if s["name"] == "query_execution")
    assert exec_stage["status"] == "SKIPPED"


def test_api_schema(api_client):
    """Verify /api/schema returns table definitions, column types, and sample rows."""
    resp = api_client.get("/api/schema")
    assert resp.status_code == 200
    data = resp.json()

    assert "tables" in data
    table_names = [t["name"].lower() for t in data["tables"]]
    assert "customers" in table_names
    assert "products" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names

    # Check sample rows on customers
    cust = next(t for t in data["tables"] if t["name"].lower() == "customers")
    assert len(cust["sample_rows"]) > 0
    assert "first_name" in cust["sample_rows"][0]


def test_api_history(api_client):
    """Verify /api/history retains recent submitted queries."""
    # Submit a query first
    api_client.post("/api/query", json={"question": "What was our total revenue in September 2026?"})

    resp = api_client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any("September 2026" in item["question"] for item in data)


def test_api_evaluation(api_client):
    """Verify /api/evaluation retrieves real benchmark metrics."""
    resp = api_client.get("/api/evaluation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sql_execution_accuracy_pct"] == 100.0
    assert data["safety_rejection_rate_pct"] == 100.0
    assert data["safety_violations"] == 0
    assert len(data["results"]) >= 15
