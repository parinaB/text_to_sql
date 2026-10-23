"""Comprehensive security test suite for AST-based SQL policy validation."""

import pytest
from database import init_database
from schema_inspector import inspect_database
from sql_validator import SQLValidator, ValidationResult


@pytest.fixture
def validator(temp_db_path):
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)
    return SQLValidator(allowed_tables={"customers", "products", "orders", "order_items"}, schema=schema)


# ==============================================================================
# PERMITTED QUERIES
# ==============================================================================

def test_permitted_basic_select(validator):
    res = validator.validate("SELECT * FROM orders;")
    assert res.is_valid is True
    assert "orders" in res.tables_accessed


def test_permitted_aggregate_query(validator):
    res = validator.validate(
        "SELECT COUNT(*) AS cnt, SUM(total_amount) AS total, AVG(total_amount) AS avg_amt FROM orders WHERE order_status = 'completed';"
    )
    assert res.is_valid is True
    assert "orders" in res.tables_accessed


def test_permitted_multi_table_join(validator):
    query = """
    SELECT c.first_name, o.order_id, oi.quantity, p.product_name
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.order_date >= '2026-10-01';
    """
    res = validator.validate(query)
    assert res.is_valid is True
    assert res.tables_accessed == {"customers", "orders", "order_items", "products"}


def test_permitted_parameterized_query(validator):
    res = validator.validate("SELECT * FROM orders WHERE total_amount > :min_amount AND shipping_city = :city;")
    assert res.is_valid is True


def test_permitted_cte(validator):
    query = """
    WITH monthly_orders AS (
        SELECT order_id, customer_id, total_amount
        FROM orders
        WHERE order_date >= '2026-10-01'
    )
    SELECT * FROM monthly_orders WHERE total_amount > 100;
    """
    res = validator.validate(query)
    assert res.is_valid is True
    # Physical table should be orders, CTE alias monthly_orders is not treated as a missing physical table
    assert res.tables_accessed == {"orders"}


def test_permitted_subquery(validator):
    query = """
    SELECT * FROM orders
    WHERE customer_id IN (
        SELECT customer_id FROM customers WHERE city = 'New York'
    );
    """
    res = validator.validate(query)
    assert res.is_valid is True
    assert res.tables_accessed == {"orders", "customers"}


def test_permitted_scalar_select(validator):
    res = validator.validate("SELECT 1 + 1 AS math_result;")
    assert res.is_valid is True


# ==============================================================================
# PROHIBITED QUERIES: MUTATING DML & DDL
# ==============================================================================

@pytest.mark.parametrize("prohibited_sql", [
    "INSERT INTO customers (customer_id, first_name) VALUES (999, 'Hacker');",
    "UPDATE products SET unit_price = 0.0 WHERE product_id = 1;",
    "DELETE FROM orders WHERE order_id = 101;",
    "DROP TABLE customers;",
    "ALTER TABLE orders ADD COLUMN backdoored TEXT;",
    "CREATE TABLE evil_table (id INT);",
    "CREATE VIEW stolen AS SELECT * FROM customers;",
    "PRAGMA table_info(orders);",
    "ATTACH DATABASE 'evil.db' AS evil;",
    "DETACH DATABASE evil;",
    "VACUUM;",
    "REINDEX;",
])
def test_prohibited_mutating_statements_rejected(validator, prohibited_sql):
    res = validator.validate(prohibited_sql)
    assert res.is_valid is False
    assert res.error_message is not None


# ==============================================================================
# PROHIBITED: MULTIPLE STATEMENTS / SEMICOLON CHAINING
# ==============================================================================

@pytest.mark.parametrize("chained_sql", [
    "SELECT * FROM orders; DROP TABLE customers;",
    "SELECT 1; SELECT 2;",
    "SELECT * FROM orders; DELETE FROM products WHERE 1=1;",
    "SELECT * FROM customers; INSERT INTO customers VALUES (999, 'evil');",
])
def test_multiple_statements_rejected(validator, chained_sql):
    res = validator.validate(chained_sql)
    assert res.is_valid is False
    assert "multiple" in res.error_message.lower() or "prohibited" in res.error_message.lower()


# ==============================================================================
# PROHIBITED: UNAUTHORIZED TABLES
# ==============================================================================

@pytest.mark.parametrize("unauthorized_sql", [
    "SELECT * FROM internal_secrets;",
    "SELECT * FROM sqlite_master;",
    "SELECT * FROM orders JOIN credentials ON orders.customer_id = credentials.id;",
    "SELECT * FROM (SELECT * FROM forbidden_financials);",
    "SELECT * FROM orders UNION ALL SELECT * FROM system_users;",
])
def test_unauthorized_tables_rejected(validator, unauthorized_sql):
    res = validator.validate(unauthorized_sql)
    assert res.is_valid is False
    assert "unauthorized" in res.error_message.lower()


# ==============================================================================
# EVASION ATTEMPTS: COMMENTS, NESTING, FUNCTIONS
# ==============================================================================

def test_comment_wrapped_statement_is_sanitized_or_blocked(validator):
    # Valid query with embedded comment
    sql1 = "SELECT * FROM orders /* Just a comment */ WHERE total_amount > 50;"
    res1 = validator.validate(sql1)
    assert res1.is_valid is True

    # Semicolon followed by comment and secondary statement
    sql2 = "SELECT * FROM orders; /* comment */ DROP TABLE customers;"
    res2 = validator.validate(sql2)
    assert res2.is_valid is False


def test_dangerous_functions_rejected(validator):
    res = validator.validate("SELECT load_extension('malicious.dylib');")
    assert res.is_valid is False
    assert "dangerous function" in res.error_message.lower()


def test_invalid_column_rejected(validator):
    res = validator.validate("SELECT orders.non_existent_column_xyz FROM orders;")
    assert res.is_valid is False
    assert "does not exist on table 'orders'" in res.error_message
