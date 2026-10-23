"""Database management: schema creation, idempotent seeding, and read-only connection factory."""

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'inactive', 'churned'))
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    cost REAL NOT NULL CHECK(cost >= 0),
    stock_quantity INTEGER NOT NULL CHECK(stock_quantity >= 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    order_date TEXT NOT NULL,
    order_status TEXT NOT NULL CHECK(order_status IN ('completed', 'pending', 'cancelled', 'shipped')),
    total_amount REAL NOT NULL CHECK(total_amount >= 0),
    shipping_city TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    discount REAL NOT NULL DEFAULT 0.0 CHECK(discount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
"""

# Fixed, reproducible seed records
CUSTOMERS_DATA = [
    (1, "Alice", "Smith", "alice.smith@example.com", "New York", "USA", "2026-01-15", "active"),
    (2, "Bob", "Jones", "bob.jones@example.com", "San Francisco", "USA", "2026-02-20", "active"),
    (3, "Charlie", "Brown", "charlie.brown@example.com", "London", "UK", "2026-03-05", "active"),
    (4, "Diana", "Prince", "diana.prince@example.com", "Berlin", "Germany", "2026-03-22", "active"),
    (5, "Evan", "Wright", "evan.wright@example.com", "New York", "USA", "2026-04-10", "inactive"),
    (6, "Fiona", "Gallagher", "fiona.g@example.com", "Chicago", "USA", "2026-05-18", "active"),
    (7, "George", "Clark", "george.c@example.com", "London", "UK", "2026-06-01", "churned"),
    (8, "Hannah", "Abbott", "hannah.a@example.com", "Tokyo", "Japan", "2026-07-14", "active"),
    (9, "Ian", "Malcolm", "ian.m@example.com", "Austin", "USA", "2026-08-09", "active"),
    (10, "Julia", "Roberts", "julia.r@example.com", "Paris", "France", "2026-09-01", "active"), # Customer with zero orders
]

PRODUCTS_DATA = [
    (1, "Wireless Noise-Canceling Headphones", "Electronics", 199.99, 90.00, 150, 1),
    (2, "Ultra-Slim Mechanical Keyboard", "Electronics", 129.50, 55.00, 80, 1),
    (3, "Ergonomic Office Chair", "Furniture", 349.00, 180.00, 45, 1),
    (4, "4K Ultra-HD Monitor 27-inch", "Electronics", 399.99, 220.00, 60, 1),
    (5, "USB-C Multi-Port Docking Station", "Accessories", 79.99, 32.00, 200, 1),
    (6, "Adjustable Standing Desk", "Furniture", 499.00, 260.00, 30, 1),
    (7, "Precision Wireless Mouse", "Accessories", 49.99, 18.00, 120, 1),
    (8, "Executive Leather Desk Pad", "Office Supplies", 39.99, 12.00, 75, 1), # Product never ordered
]

ORDERS_DATA = [
    # October 2026 Orders
    (101, 1, "2026-10-02", "completed", 329.49, "New York"),
    (102, 2, "2026-10-05", "completed", 399.99, "San Francisco"),
    (103, 3, "2026-10-10", "completed", 548.99, "London"),
    (104, 4, "2026-10-12", "shipped", 129.50, "Berlin"),
    (105, 1, "2026-10-15", "completed", 79.99, "New York"),
    (106, 6, "2026-10-18", "pending", 499.00, "Chicago"),
    (107, 8, "2026-10-20", "completed", 249.98, "Tokyo"),
    (108, 9, "2026-10-22", "cancelled", 349.00, "Austin"),
    # September 2026 Orders
    (109, 1, "2026-09-03", "completed", 199.99, "New York"),
    (110, 2, "2026-09-11", "completed", 479.98, "San Francisco"),
    (111, 3, "2026-09-15", "completed", 399.99, "London"),
    (112, 5, "2026-09-21", "completed", 49.99, "New York"),
    (113, 7, "2026-09-28", "completed", 129.50, "London"),
    # August 2026 Orders
    (114, 4, "2026-08-08", "completed", 848.00, "Berlin"),
    (115, 6, "2026-08-19", "completed", 79.99, "Chicago"),
]

ORDER_ITEMS_DATA = [
    # Order 101: 1 Headphone ($199.99), 1 Keyboard ($129.50) = $329.49
    (1, 101, 1, 1, 199.99, 0.0),
    (2, 101, 2, 1, 129.50, 0.0),
    # Order 102: 1 Monitor ($399.99)
    (3, 102, 4, 1, 399.99, 0.0),
    # Order 103: 1 Headphone ($199.99), 1 Chair ($349.00) = $548.99
    (4, 103, 1, 1, 199.99, 0.0),
    (5, 103, 3, 1, 349.00, 0.0),
    # Order 104: 1 Keyboard ($129.50)
    (6, 104, 2, 1, 129.50, 0.0),
    # Order 105: 1 Docking Station ($79.99)
    (7, 105, 5, 1, 79.99, 0.0),
    # Order 106: 1 Standing Desk ($499.00)
    (8, 106, 6, 1, 499.00, 0.0),
    # Order 107: 1 Headphone ($199.99), 1 Mouse ($49.99) = $249.98
    (9, 107, 1, 1, 199.99, 0.0),
    (10, 107, 7, 1, 49.99, 0.0),
    # Order 108: 1 Chair ($349.00)
    (11, 108, 3, 1, 349.00, 0.0),
    # Order 109: 1 Headphone ($199.99)
    (12, 109, 1, 1, 199.99, 0.0),
    # Order 110: 1 Monitor ($399.99), 1 Docking Station ($79.99) = $479.98
    (13, 110, 4, 1, 399.99, 0.0),
    (14, 110, 5, 1, 79.99, 0.0),
    # Order 111: 1 Monitor ($399.99)
    (15, 111, 4, 1, 399.99, 0.0),
    # Order 112: 1 Mouse ($49.99)
    (16, 112, 7, 1, 49.99, 0.0),
    # Order 113: 1 Keyboard ($129.50)
    (17, 113, 2, 1, 129.50, 0.0),
    # Order 114: 1 Chair ($349.00), 1 Standing Desk ($499.00) = $848.00
    (18, 114, 3, 1, 349.00, 0.0),
    (19, 114, 6, 1, 499.00, 0.0),
    # Order 115: 1 Docking Station ($79.99)
    (20, 115, 5, 1, 79.99, 0.0),
]


def init_database(db_path: str = "business.db") -> None:
    """Initialize database schema and populate with idempotent seed data."""
    path_obj = Path(db_path).resolve()
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path_obj))
    try:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)

        # Idempotent seed data insertion
        cursor.executemany(
            """INSERT OR REPLACE INTO customers 
               (customer_id, first_name, last_name, email, city, country, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            CUSTOMERS_DATA,
        )

        cursor.executemany(
            """INSERT OR REPLACE INTO products
               (product_id, product_name, category, unit_price, cost, stock_quantity, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            PRODUCTS_DATA,
        )

        cursor.executemany(
            """INSERT OR REPLACE INTO orders
               (order_id, customer_id, order_date, order_status, total_amount, shipping_city)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ORDERS_DATA,
        )

        cursor.executemany(
            """INSERT OR REPLACE INTO order_items
               (item_id, order_id, product_id, quantity, unit_price, discount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ORDER_ITEMS_DATA,
        )

        conn.commit()
    finally:
        conn.close()


def get_readonly_connection(db_path: str = "business.db", timeout_seconds: float = 5.0) -> sqlite3.Connection:
    """Create an isolated, read-only SQLite connection.
    
    Uses SQLite URI mode 'mode=ro' and enforces query_only PRAGMA.
    """
    path_obj = Path(db_path).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"Database file does not exist: {path_obj}")

    # SQLite URI for read-only connection
    uri = f"file:{path_obj.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=timeout_seconds)
    conn.row_factory = sqlite3.Row

    # Enforce read-only at the SQLite engine level
    cursor = conn.cursor()
    cursor.execute("PRAGMA query_only = ON;")
    cursor.close()

    return conn


def get_table_counts(db_path: str = "business.db") -> Dict[str, int]:
    """Retrieve row counts for all approved tables."""
    conn = get_readonly_connection(db_path)
    try:
        cursor = conn.cursor()
        counts = {}
        for table in ["customers", "products", "orders", "order_items"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        return counts
    finally:
        conn.close()
