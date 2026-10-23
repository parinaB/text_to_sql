"""Unit and integration tests for database schema, idempotency, and read-only mode."""

import sqlite3
import pytest
from database import init_database, get_readonly_connection, get_table_counts


def test_database_initialization_and_counts(temp_db_path):
    """Verify database initialization creates tables with exact seed row counts."""
    init_database(temp_db_path)
    counts = get_table_counts(temp_db_path)

    assert counts["customers"] == 10
    assert counts["products"] == 8
    assert counts["orders"] == 15
    assert counts["order_items"] == 20


def test_database_idempotency(temp_db_path):
    """Verify initializing database twice does not duplicate records or fail."""
    init_database(temp_db_path)
    init_database(temp_db_path)

    counts = get_table_counts(temp_db_path)
    assert counts["customers"] == 10
    assert counts["products"] == 8
    assert counts["orders"] == 15
    assert counts["order_items"] == 20


def test_representative_queries(temp_db_path):
    """Verify representative business queries return accurate, expected results."""
    init_database(temp_db_path)
    conn = get_readonly_connection(temp_db_path)
    cursor = conn.cursor()

    # Query 1: Total orders in October 2026
    cursor.execute(
        "SELECT COUNT(*) AS total_october_orders FROM orders WHERE order_date >= '2026-10-01' AND order_date <= '2026-10-31'"
    )
    assert cursor.fetchone()[0] == 8

    # Query 2: Product never ordered (Product ID 8: Executive Leather Desk Pad)
    cursor.execute(
        """SELECT p.product_name 
           FROM products p 
           LEFT JOIN order_items oi ON p.product_id = oi.product_id 
           WHERE oi.product_id IS NULL"""
    )
    unorderd_products = [row[0] for row in cursor.fetchall()]
    assert "Executive Leather Desk Pad" in unorderd_products

    # Query 3: Customer with 0 orders (Customer ID 10: Julia Roberts)
    cursor.execute(
        """SELECT c.first_name, c.last_name 
           FROM customers c 
           LEFT JOIN orders o ON c.customer_id = o.customer_id 
           WHERE o.order_id IS NULL"""
    )
    unorderd_customers = [f"{row[0]} {row[1]}" for row in cursor.fetchall()]
    assert "Julia Roberts" in unorderd_customers

    # Query 4: Total revenue in September 2026
    cursor.execute(
        "SELECT SUM(total_amount) FROM orders WHERE order_date >= '2026-09-01' AND order_date <= '2026-09-30'"
    )
    sept_rev = cursor.fetchone()[0]
    # Sum of orders 109 to 113: 199.99 + 479.98 + 399.99 + 49.99 + 129.50 = 1259.45
    assert round(sept_rev, 2) == 1259.45

    conn.close()


def test_readonly_connection_blocks_mutations(temp_db_path):
    """Verify that read-only connection strictly prevents INSERT, UPDATE, DELETE, and DROP."""
    init_database(temp_db_path)
    conn = get_readonly_connection(temp_db_path)
    cursor = conn.cursor()

    # Attempt INSERT
    with pytest.raises(sqlite3.OperationalError) as exc_info:
        cursor.execute("INSERT INTO customers (customer_id, first_name, last_name, email, city, country, created_at, status) VALUES (999, 'Hacker', 'X', 'h@x.com', 'Nowhere', 'Nowhere', '2026-10-01', 'active')")
    assert "readonly" in str(exc_info.value).lower()

    # Attempt UPDATE
    with pytest.raises(sqlite3.OperationalError) as exc_info:
        cursor.execute("UPDATE products SET unit_price = 0 WHERE product_id = 1")
    assert "readonly" in str(exc_info.value).lower()

    # Attempt DELETE
    with pytest.raises(sqlite3.OperationalError) as exc_info:
        cursor.execute("DELETE FROM orders WHERE order_id = 101")
    assert "readonly" in str(exc_info.value).lower()

    # Attempt DROP
    with pytest.raises(sqlite3.OperationalError) as exc_info:
        cursor.execute("DROP TABLE customers")
    assert "readonly" in str(exc_info.value).lower()

    conn.close()


def test_nonexistent_database_raises_error(tmp_path):
    """Verify get_readonly_connection raises FileNotFoundError for missing db."""
    missing_path = tmp_path / "does_not_exist.db"
    with pytest.raises(FileNotFoundError):
        get_readonly_connection(str(missing_path))
