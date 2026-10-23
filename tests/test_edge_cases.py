"""Comprehensive edge-case and boundary test suite for Text-to-SQL Agent."""

import json
import pytest
from config import AppConfig
from database import init_database, get_readonly_connection, get_table_counts
from schema_inspector import inspect_database
from sql_validator import SQLValidator, ValidationResult
from query_executor import (
    ReadOnlyQueryExecutor,
    ValidatedQuery,
    ExecutionResult,
)
from answer_formatter import AnswerFormatter
from agent import TextToSQLAgent
from embeddings import DeterministicTestEmbeddingProvider
from retriever import index_all_context, retrieve_context


@pytest.fixture
def edge_fixture(temp_db_path, temp_chroma_dir):
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)
    validator = SQLValidator(allowed_tables={"customers", "products", "orders", "order_items"}, schema=schema)
    cfg = AppConfig(
        database_path=temp_db_path,
        chroma_persist_dir=temp_chroma_dir,
        query_timeout_seconds=2.0,
        max_result_rows=10,
    )
    executor = ReadOnlyQueryExecutor(db_path=temp_db_path, config=cfg)
    agent = TextToSQLAgent(config=cfg)
    return {
        "db_path": temp_db_path,
        "chroma_dir": temp_chroma_dir,
        "schema": schema,
        "validator": validator,
        "executor": executor,
        "agent": agent,
        "config": cfg,
    }


# ==============================================================================
# 1. SQL VALIDATOR SECURITY & PARSER EDGE CASES
# ==============================================================================

@pytest.mark.parametrize("mixed_case_sql", [
    "sElEcT * FrOm orders;",
    "SELECT * FROM Orders WHERE total_Amount > 100;",
    "wItH oct_orders AS (sElEcT * fRoM orders) SELECT * FROM oct_orders;",
])
def test_sql_case_insensitivity_permitted(edge_fixture, mixed_case_sql):
    """Verify parser permits case-insensitive keywords for valid queries."""
    res = edge_fixture["validator"].validate(mixed_case_sql)
    assert res.is_valid is True


@pytest.mark.parametrize("mixed_case_attack", [
    "sElEcT 1; dRoP tAbLe customers;",
    "iNsErT iNtO customers VALUES (999, 'evil', 'evil', 'e@e.com', 'x', 'x', '2026-01-01', 'active');",
    "uPdAtE products sEt unit_price = 0;",
    "dElEtE fRoM orders;",
    "cReAtE tAbLe evil (x INT);",
    "aLtEr tAbLe orders aDd cOlUmN x TEXT;",
])
def test_sql_mixed_case_attacks_rejected(edge_fixture, mixed_case_attack):
    """Verify parser rejects mutating statements regardless of mixed casing."""
    res = edge_fixture["validator"].validate(mixed_case_attack)
    assert res.is_valid is False


def test_sql_comment_obfuscation(edge_fixture):
    """Verify inline and multiline comments cannot mask attacks or break valid queries."""
    validator = edge_fixture["validator"]

    # Valid query with internal comments
    sql_valid = "SELECT /*comment*/ order_id, /*another*/ total_amount FROM orders /*table comment*/ WHERE 1=1;"
    res1 = validator.validate(sql_valid)
    assert res1.is_valid is True

    # Line comment containing dangerous keywords (not executed)
    sql_line_comment = "SELECT * FROM orders -- comment mentioning DROP TABLE customers\n WHERE total_amount > 50;"
    res2 = validator.validate(sql_line_comment)
    assert res2.is_valid is True

    # Attack: Semicolon followed by comment and second statement
    sql_attack = "SELECT * FROM orders; /* comment */ DROP TABLE customers;"
    res3 = validator.validate(sql_attack)
    assert res3.is_valid is False
    assert "multiple" in res3.error_message.lower() or "prohibited" in res3.error_message.lower()


def test_sql_complex_clauses_permitted(edge_fixture):
    """Verify support for CASE statements, Window Functions, and Subqueries in SELECT."""
    validator = edge_fixture["validator"]
    executor = edge_fixture["executor"]

    # 1. CASE WHEN statement
    sql_case = """
    SELECT order_id, total_amount,
           CASE WHEN total_amount >= 400 THEN 'HIGH'
                WHEN total_amount >= 200 THEN 'MEDIUM'
                ELSE 'LOW' END AS order_tier
    FROM orders
    LIMIT 5;
    """
    res1 = validator.validate(sql_case)
    assert res1.is_valid is True
    exec1 = executor.execute(ValidatedQuery(sql=sql_case, validation_result=res1))
    assert exec1.success is True
    assert "order_tier" in exec1.columns

    # 2. Window Function (ROW_NUMBER OVER)
    sql_window = """
    SELECT order_id, customer_id, total_amount,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total_amount DESC) as rank_per_customer
    FROM orders;
    """
    res2 = validator.validate(sql_window)
    assert res2.is_valid is True
    exec2 = executor.execute(ValidatedQuery(sql=sql_window, validation_result=res2))
    assert exec2.success is True
    assert "rank_per_customer" in exec2.columns

    # 3. Scalar Subquery in SELECT clause
    sql_subquery = """
    SELECT c.customer_id, c.first_name,
           (SELECT MAX(o.total_amount) FROM orders o WHERE o.customer_id = c.customer_id) AS max_spend
    FROM customers c
    LIMIT 5;
    """
    res3 = validator.validate(sql_subquery)
    assert res3.is_valid is True
    exec3 = executor.execute(ValidatedQuery(sql=sql_subquery, validation_result=res3))
    assert exec3.success is True
    assert "max_spend" in exec3.columns


def test_sql_prohibited_sqlite_special_tables(edge_fixture):
    """Verify internal SQLite system tables are prohibited by table allowlist."""
    validator = edge_fixture["validator"]
    for tbl in ["sqlite_sequence", "sqlite_temp_master", "sqlite_stat1", "sqlite_schema"]:
        sql = f"SELECT * FROM {tbl};"
        res = validator.validate(sql)
        assert res.is_valid is False
        assert "unauthorized" in res.error_message.lower()


def test_sql_cte_referencing_unauthorized_table_rejected(edge_fixture):
    """Verify that a CTE referencing an unauthorized table is caught and rejected."""
    validator = edge_fixture["validator"]
    sql = "WITH stolen_data AS (SELECT * FROM secret_passwords) SELECT * FROM stolen_data;"
    res = validator.validate(sql)
    assert res.is_valid is False
    assert "secret_passwords" in res.error_message.lower()


def test_sql_nested_ctes_permitted(edge_fixture):
    """Verify chained/nested CTEs referencing allowed tables pass validation."""
    validator = edge_fixture["validator"]
    sql = """
    WITH step1 AS (
        SELECT customer_id, total_amount FROM orders WHERE total_amount > 100
    ),
    step2 AS (
        SELECT customer_id, SUM(total_amount) AS customer_total FROM step1 GROUP BY customer_id
    )
    SELECT * FROM step2 WHERE customer_total > 300;
    """
    res = validator.validate(sql)
    assert res.is_valid is True
    assert res.tables_accessed == {"orders"}


# ==============================================================================
# 2. QUERY EXECUTOR & PARAMETER INJECTION EDGE CASES
# ==============================================================================

def test_sql_parameter_injection_resistance(edge_fixture):
    """Verify that malicious input passed as a bound parameter cannot alter query logic."""
    validator = edge_fixture["validator"]
    executor = edge_fixture["executor"]

    sql = "SELECT * FROM customers WHERE first_name = :search_name;"
    val_res = validator.validate(sql)
    assert val_res.is_valid is True

    # Parameter value attempting classic SQL injection: ' OR '1'='1
    malicious_param = "' OR '1'='1"
    query = ValidatedQuery(
        sql=sql,
        parameters={"search_name": malicious_param},
        validation_result=val_res,
    )

    result = executor.execute(query)
    assert result.success is True
    # Should find ZERO rows because no customer's literal first_name is "' OR '1'='1"
    assert result.row_count == 0
    assert result.is_empty is True


def test_executor_parameter_types_handling(edge_fixture):
    """Verify executor safely binds various python types (int, float, str, None)."""
    validator = edge_fixture["validator"]
    executor = edge_fixture["executor"]

    sql = """
    SELECT * FROM order_items
    WHERE quantity >= :min_qty
      AND unit_price <= :max_price
      AND (:opt_discount IS NULL OR discount >= :opt_discount);
    """
    val_res = validator.validate(sql)
    assert val_res.is_valid is True

    query = ValidatedQuery(
        sql=sql,
        parameters={
            "min_qty": 1,
            "max_price": 250.00,
            "opt_discount": None,
        },
        validation_result=val_res,
    )
    res = executor.execute(query)
    assert res.success is True
    assert res.row_count > 0


def test_executor_exact_row_limit_boundaries(edge_fixture):
    """Test exact boundary conditions around max_result_rows."""
    db_path = edge_fixture["db_path"]
    validator = edge_fixture["validator"]

    # Case A: exactly max_rows
    cfg_exact = AppConfig(database_path=db_path, max_result_rows=15)
    exec_exact = ReadOnlyQueryExecutor(db_path=db_path, config=cfg_exact)
    sql = "SELECT order_id FROM orders;" # Exactly 15 orders in seed data
    val_res = validator.validate(sql)

    res_exact = exec_exact.execute(ValidatedQuery(sql=sql, validation_result=val_res))
    assert res_exact.row_count == 15
    assert res_exact.is_truncated is False

    # Case B: max_rows < total rows
    cfg_trunc = AppConfig(database_path=db_path, max_result_rows=14)
    exec_trunc = ReadOnlyQueryExecutor(db_path=db_path, config=cfg_trunc)

    res_trunc = exec_trunc.execute(ValidatedQuery(sql=sql, validation_result=val_res))
    assert res_trunc.row_count == 14
    assert res_trunc.is_truncated is True


def test_executor_aggregation_on_zero_rows(edge_fixture):
    """Verify handling of SQL aggregate functions on empty result sets returning None values."""
    validator = edge_fixture["validator"]
    executor = edge_fixture["executor"]

    sql = "SELECT COUNT(*) AS cnt, AVG(total_amount) AS avg_amt, SUM(total_amount) AS sum_amt FROM orders WHERE 1=0;"
    val_res = validator.validate(sql)

    res = executor.execute(ValidatedQuery(sql=sql, validation_result=val_res))
    assert res.success is True
    assert res.row_count == 1
    assert res.rows[0]["cnt"] == 0
    assert res.rows[0]["avg_amt"] is None
    assert res.rows[0]["sum_amt"] is None


# ==============================================================================
# 3. EMBEDDINGS & RETRIEVER EDGE CASES
# ==============================================================================

def test_embeddings_unicode_and_emojis():
    """Verify embedding provider handles non-ASCII characters, emojis, and multilingual text."""
    provider = DeterministicTestEmbeddingProvider(dimension=128)

    texts = [
        "How many orders did we receive? 🚀📦🛒",
        "Café orders in São Paulo and Zürich",
        "2026年10月の注文総数はいくつですか？",
        "Пользователи и заказы",
    ]
    for t in texts:
        vec = provider.embed_text(t)
        assert len(vec) == 128
        assert not any(x != x for x in vec) # No NaN values


def test_embeddings_very_long_input():
    """Verify embedding provider processes massive input without memory or hashing errors."""
    provider = DeterministicTestEmbeddingProvider(dimension=128)
    long_text = "order customer product " * 2000 # 6000 words
    vec = provider.embed_text(long_text)
    assert len(vec) == 128
    assert sum(x * x for x in vec) > 0.0


def test_embeddings_symbols_only():
    """Verify embedding provider handles symbol-only inputs cleanly."""
    provider = DeterministicTestEmbeddingProvider(dimension=128)
    vec = provider.embed_text("!@#$%^&*()_+=-{}[]:;'\"<>,.?/")
    assert len(vec) == 128


def test_retriever_top_k_larger_than_collection(temp_chroma_dir):
    """Verify requesting top_k larger than collection size caps safely without error."""
    provider = DeterministicTestEmbeddingProvider(dimension=128)
    index_all_context(chroma_dir=temp_chroma_dir, provider=provider)

    ctx = retrieve_context(
        question="Show me orders",
        chroma_dir=temp_chroma_dir,
        top_k_schema=50, # Collection has only 4 docs
        top_k_examples=50, # Collection has only 7 docs
        provider=provider,
    )
    assert len(ctx.schema_snippets) == 4
    assert len(ctx.few_shot_examples) == 7


# ==============================================================================
# 4. ANSWER FORMATTER & AGENT EDGE CASES
# ==============================================================================

def test_formatter_null_and_negative_values():
    """Verify answer formatter formats nulls and negative amounts gracefully."""
    formatter = AnswerFormatter()

    # Null values in columns
    res_null = ExecutionResult(
        success=True,
        rows=[{"category": "Electronics", "avg_discount": None}],
        columns=["category", "avg_discount"],
        row_count=1,
    )
    ans1 = formatter.format_success("Average discount", res_null, [], "")
    assert "None" in ans1 or "Electronics" in ans1

    # Single scalar negative value
    res_neg = ExecutionResult(
        success=True,
        rows=[{"profit_loss": -450.50}],
        columns=["profit_loss"],
        row_count=1,
    )
    ans2 = formatter.format_success("Net profit", res_neg, [], "")
    assert "Result:" in ans2


def test_formatter_multi_column_single_row():
    """Verify multi-column single row output formats as a table rather than scalar string."""
    formatter = AnswerFormatter()
    res = ExecutionResult(
        success=True,
        rows=[{"customer_id": 1, "first_name": "Alice", "total_orders": 3}],
        columns=["customer_id", "first_name", "total_orders"],
        row_count=1,
    )
    ans = formatter.format_success("Customer details", res, [], "")
    assert "| customer_id | first_name | total_orders |" in ans
    assert "Alice" in ans


def test_agent_unique_request_ids(edge_fixture):
    """Verify each invocation receives a distinct request_id."""
    agent = edge_fixture["agent"]
    r1 = agent.ask("How many orders did we receive in October 2026?")
    r2 = agent.ask("How many orders did we receive in October 2026?")

    assert r1.request_id != r2.request_id
    assert r1.request_id.startswith("req_")
    assert r2.request_id.startswith("req_")


def test_app_run_cli(capsys):
    """Verify run_cli function executes and prints structured sections to stdout."""
    from app import run_cli
    run_cli("How many orders did we receive in October 2026?")
    captured = capsys.readouterr().out
    assert "TEXT-TO-SQL AGENT: CLI EXECUTION" in captured
    assert "Validation Status: PASSED" in captured
    assert "Natural-Language Answer:" in captured

