"""Unit tests for dynamic SQLite schema inspector."""

import sqlite3
import pytest
from database import init_database
from schema_inspector import inspect_database, DatabaseSchema


def test_inspect_business_database(temp_db_path):
    """Verify inspection retrieves tables, columns, and constraints from SQLite."""
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)

    assert set(schema.get_table_names()) == {"customers", "products", "orders", "order_items"}

    # Test customers table
    cust_table = schema.get_table("customers")
    assert cust_table is not None
    assert cust_table.primary_keys == ["customer_id"]
    assert "email" in cust_table.column_names
    assert "city" in cust_table.column_names
    assert cust_table.has_column("FIRST_NAME")

    # Test orders table and foreign key
    orders_table = schema.get_table("orders")
    assert orders_table is not None
    assert orders_table.primary_keys == ["order_id"]
    fk_customers = [fk for fk in orders_table.foreign_keys if fk.foreign_table.lower() == "customers"]
    assert len(fk_customers) == 1
    assert fk_customers[0].column == "customer_id"
    assert fk_customers[0].foreign_column == "customer_id"


def test_unauthorized_tables_excluded(temp_db_path):
    """Verify unauthorized tables are strictly omitted from inspected schema context."""
    init_database(temp_db_path)

    # Insert an unauthorized secret table
    conn = sqlite3.connect(temp_db_path)
    conn.execute("CREATE TABLE internal_secrets (secret_id INT PRIMARY KEY, token TEXT);")
    conn.execute("INSERT INTO internal_secrets VALUES (1, 'super-secret-token');")
    conn.commit()
    conn.close()

    # Inspect with allowed_tables specified
    allowed = {"customers", "products", "orders", "order_items"}
    schema = inspect_database(temp_db_path, allowed_tables=allowed)

    assert "internal_secrets" not in schema.get_table_names()
    assert not schema.is_valid_table("internal_secrets")
    assert schema.is_valid_table("customers")


def test_schema_adaptation_on_table_addition(temp_db_path):
    """Verify inspector dynamically discovers newly added approved tables."""
    init_database(temp_db_path)

    conn = sqlite3.connect(temp_db_path)
    conn.execute("""
        CREATE TABLE suppliers (
            supplier_id INTEGER PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            contact_email TEXT
        );
    """)
    conn.commit()
    conn.close()

    schema = inspect_database(temp_db_path, allowed_tables={"customers", "products", "orders", "order_items", "suppliers"})
    assert schema.is_valid_table("suppliers")
    supplier_tbl = schema.get_table("suppliers")
    assert supplier_tbl.primary_keys == ["supplier_id"]
    assert "supplier_name" in supplier_tbl.column_names


def test_empty_database_inspection(tmp_path):
    """Verify inspecting an empty SQLite database returns an empty DatabaseSchema."""
    empty_db = tmp_path / "empty.db"
    conn = sqlite3.connect(str(empty_db))
    conn.close()

    schema = inspect_database(str(empty_db))
    assert len(schema.get_table_names()) == 0
    assert schema.to_markdown() == "No tables available."


def test_missing_database_raises_error(tmp_path):
    """Verify inspecting a missing file raises FileNotFoundError."""
    missing = tmp_path / "absent.db"
    with pytest.raises(FileNotFoundError):
        inspect_database(str(missing))


def test_markdown_and_ddl_generation(temp_db_path):
    """Verify markdown and DDL representations contain expected table definitions."""
    init_database(temp_db_path)
    schema = inspect_database(temp_db_path)

    markdown = schema.to_markdown()
    assert "### Table: `customers`" in markdown
    assert "FK -> `customers.customer_id`" in markdown

    ddl = schema.to_ddl_summary()
    assert "CREATE TABLE customers (" in ddl
    assert "FOREIGN KEY (customer_id) REFERENCES customers(customer_id)" in ddl
