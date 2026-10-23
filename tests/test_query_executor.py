"""Integration and safety tests for ReadOnlyQueryExecutor."""

import pytest
from database import init_database, get_table_counts
from schema_inspector import inspect_database
from sql_validator import SQLValidator, ValidationResult
from query_executor import (
    ReadOnlyQueryExecutor,
    ValidatedQuery,
    ExecutionResult,
    UnvalidatedQueryExecutionError,
)
from config import AppConfig


@pytest.fixture
def executor_and_validator(temp_db_path):
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)
    validator = SQLValidator(allowed_tables={"customers", "products", "orders", "order_items"}, schema=schema)
    cfg = AppConfig(database_path=temp_db_path, query_timeout_seconds=1.0, max_result_rows=10)
    executor = ReadOnlyQueryExecutor(db_path=temp_db_path, config=cfg)
    return executor, validator, temp_db_path


def test_execute_valid_query(executor_and_validator):
    executor, validator, _ = executor_and_validator
    sql = "SELECT COUNT(*) AS total_orders FROM orders WHERE order_date >= '2026-10-01' AND order_date <= '2026-10-31';"
    val_res = validator.validate(sql)
    assert val_res.is_valid is True

    valid_q = ValidatedQuery(sql=sql, validation_result=val_res)
    result = executor.execute(valid_q)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.row_count == 1
    assert result.rows[0]["total_orders"] == 8
    assert result.is_empty is False
    assert result.is_truncated is False
    assert result.execution_time_ms >= 0.0


def test_execute_parameterized_query(executor_and_validator):
    executor, validator, _ = executor_and_validator
    sql = "SELECT order_id, total_amount FROM orders WHERE shipping_city = :city AND total_amount > :min_val;"
    val_res = validator.validate(sql)
    assert val_res.is_valid is True

    valid_q = ValidatedQuery(
        sql=sql,
        parameters={"city": "New York", "min_val": 100.0},
        validation_result=val_res,
    )
    result = executor.execute(valid_q)

    assert result.success is True
    assert result.row_count == 2
    # Order 101 ($329.49) and Order 109 ($199.99)
    order_ids = [r["order_id"] for r in result.rows]
    assert 101 in order_ids
    assert 109 in order_ids


def test_execute_empty_result_distinguished_from_error(executor_and_validator):
    executor, validator, _ = executor_and_validator
    sql = "SELECT * FROM orders WHERE order_date = '2099-12-31';"
    val_res = validator.validate(sql)
    assert val_res.is_valid is True

    valid_q = ValidatedQuery(sql=sql, validation_result=val_res)
    result = executor.execute(valid_q)

    assert result.success is True
    assert result.is_empty is True
    assert result.row_count == 0
    assert result.rows == []
    assert result.error_message is None


def test_row_limit_truncation(temp_db_path):
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)
    validator = SQLValidator(allowed_tables={"customers", "products", "orders", "order_items"}, schema=schema)
    cfg = AppConfig(database_path=temp_db_path, max_result_rows=3)
    executor = ReadOnlyQueryExecutor(db_path=temp_db_path, config=cfg)

    sql = "SELECT order_id, order_date FROM orders ORDER BY order_id;"
    val_res = validator.validate(sql)
    valid_q = ValidatedQuery(sql=sql, validation_result=val_res)

    result = executor.execute(valid_q)
    assert result.success is True
    assert result.row_count == 3
    assert len(result.rows) == 3
    assert result.is_truncated is True


def test_timeout_interruption(temp_db_path):
    init_database(temp_db_path)
    validator = SQLValidator(allowed_tables={"customers", "products", "orders", "order_items"})
    # Configure tiny timeout
    cfg = AppConfig(database_path=temp_db_path, query_timeout_seconds=0.05)
    executor = ReadOnlyQueryExecutor(db_path=temp_db_path, config=cfg)

    # Recursive heavy query
    sql = "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt) SELECT count(*) FROM cnt WHERE x < 100000000;"
    val_res = validator.validate(sql)
    valid_q = ValidatedQuery(sql=sql, validation_result=val_res)

    result = executor.execute(valid_q)
    assert result.success is False
    assert "timed out" in result.error_message.lower()


def test_unvalidated_query_rejected():
    executor = ReadOnlyQueryExecutor(db_path="business.db")
    invalid_val = ValidationResult(is_valid=False, error_message="Policy violation")
    bad_q = ValidatedQuery(sql="DELETE FROM orders;", validation_result=invalid_val)

    with pytest.raises(UnvalidatedQueryExecutionError):
        executor.execute(bad_q)


def test_database_state_unaltered_after_execution(executor_and_validator):
    executor, validator, db_path = executor_and_validator
    counts_before = get_table_counts(db_path)

    # Run queries
    sql = "SELECT * FROM orders WHERE total_amount > 50;"
    val_res = validator.validate(sql)
    executor.execute(ValidatedQuery(sql=sql, validation_result=val_res))

    counts_after = get_table_counts(db_path)
    assert counts_before == counts_after
