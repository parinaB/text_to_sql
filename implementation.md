# Implementation Guide: Text-to-SQL AI Agent

## 1. Project Overview
The **Text-to-SQL AI Agent** is an enterprise-grade, secure assistant that transforms natural language business inquiries into ANSI SQLite queries, executes them safely against a read-only SQLite database, and returns clear, grounded explanations.

Key capabilities:
- Dynamic schema introspection directly from SQLite.
- ChromaDB vector retrieval for schema context and few-shot question-to-SQL exemplars.
- Pluggable embedding and LLM provider support (Ollama with `nomic-embed-text`, OpenAI, Gemini, and a deterministic offline test provider).
- Multi-layered AST-based SQL security verification using `sqlglot`.
- Read-only execution via `file:...mode=ro` with execution limits and timeout handlers.
- Grounded result explanation with explicit assumption reporting.
- Interactive Streamlit UI and CLI.

---

## 2. Repository Structure

```text
/Users/astitva/Desktop/sem5/
├── .env.example              # Template environment configuration
├── .gitignore                # Git ignore rules for virtualenv, db, and secrets
├── README.md                 # Project entry point and quickstart
├── decision.md               # Authoritative architecture and decision record
├── implementation.md         # Detailed implementation guide & progress checklist
├── IMPLEMENTATION_LOG.md     # Chronological audit log of verified execution steps
├── requirements.txt          # Python dependency definitions
├── config.py                 # Pydantic configuration and environment settings
├── database.py               # SQLite schema creation, seeding, and read-only connection
├── schema_inspector.py       # Dynamic schema discovery from SQLite metadata
├── embeddings.py             # Pluggable embedding providers (Ollama, cloud, deterministic)
├── retriever.py              # ChromaDB vector indexer and similarity retriever
├── prompts.py                # SQL generation and explanation prompts
├── sql_generator.py          # Structured LLM SQL generation interface
├── sql_validator.py          # AST-based SQL security policy validator
├── query_executor.py         # Restricted read-only SQLite executor
├── answer_formatter.py       # Result explanation and assumption formatter
├── agent.py                  # End-to-end pipeline orchestrator with self-healing retry
├── app.py                    # Streamlit web UI and CLI interface
├── evaluation/
│   └── dataset.json          # Benchmark evaluation questions, expected SQL, and answers
└── tests/
    ├── conftest.py           # Shared pytest fixtures
    ├── test_database.py      # Database initialization, seeding, and read-only tests
    ├── test_schema_inspector.py # Schema inspection tests
    ├── test_embeddings_retriever.py # Vector indexing and retrieval tests
    ├── test_sql_validator.py # Exhaustive security and AST validation tests
    ├── test_query_executor.py # Execution limits and timeout tests
    ├── test_agent.py         # End-to-end orchestration and self-healing tests
    └── test_evaluation.py    # Benchmark dataset evaluation suite
```

---

## 3. Setup Prerequisites

- macOS or Linux operating system.
- Python 3.11+ installed.
- SQLite 3.35+ (standard on Python 3.11+).
- (Optional) Ollama running locally on `http://localhost:11434` with `nomic-embed-text` and `qwen2.5-coder`.

---

## 4. Virtual Environment Creation & Dependency Installation

```bash
# Create Python 3.11 virtual environment
/opt/homebrew/bin/python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Environment Variable Configuration

Copy `.env.example` to `.env` and configure settings:

```bash
cp .env.example .env
```

Key variables:
- `LLM_PROVIDER`: `deterministic` (default for tests), `ollama`, `openai`, or `gemini`.
- `EMBEDDING_PROVIDER`: `deterministic` (default for tests), `ollama`, `openai`, or `gemini`.
- `OLLAMA_BASE_URL`: `http://localhost:11434` (default).
- `EMBEDDING_MODEL`: `nomic-embed-text`.
- `LLM_MODEL`: `qwen2.5-coder:7b` or `gpt-4o-mini`.
- `DATABASE_PATH`: `business.db`.
- `CHROMA_PERSIST_DIR`: `./chroma_data`.
- `MAX_RETRIES`: `2`.
- `QUERY_TIMEOUT_SECONDS`: `5.0`.
- `MAX_RESULT_ROWS`: `100`.

---

## 6. Database Initialization and Seed Data

To initialize the SQLite database with idempotent seed records:

```bash
.venv/bin/python -c "from database import init_database; init_database('business.db')"
```

Tables created:
1. `customers` (customer_id, first_name, last_name, email, city, country, created_at, status)
2. `products` (product_id, product_name, category, unit_price, cost, stock_quantity, is_active)
3. `orders` (order_id, customer_id, order_date, order_status, total_amount, shipping_city)
4. `order_items` (item_id, order_id, product_id, quantity, unit_price, discount)

---

## 7. ChromaDB Indexing

To index schema descriptions and few-shot question-to-SQL exemplars:

```bash
.venv/bin/python -c "from retriever import index_all_context; index_all_context()"
```

---

## 8. Application Startup

### Web UI (Streamlit)
```bash
.venv/bin/streamlit run app.py
```

### CLI Mode
```bash
.venv/bin/python app.py --cli "How many orders were placed in October 2026?"
```

---

## 9. Example Requests & Expected Responses

### Example 1: Aggregate Count with Date Filter
- **Question**: "How many orders did we receive in October 2026?"
- **Generated SQL**:
  ```sql
  SELECT COUNT(*) AS total_orders
  FROM orders
  WHERE order_date >= '2026-10-01' AND order_date <= '2026-10-31';
  ```
- **Explanation**: "We received 42 orders during October 2026."

### Example 2: Multi-Table Join & Top-K Ranking
- **Question**: "Which 5 products generated the highest revenue?"
- **Generated SQL**:
  ```sql
  SELECT p.product_name, SUM(oi.quantity * (oi.unit_price - oi.discount)) AS total_revenue
  FROM order_items oi
  JOIN products p ON oi.product_id = p.product_id
  GROUP BY p.product_id, p.product_name
  ORDER BY total_revenue DESC
  LIMIT 5;
  ```
- **Explanation**: "The top 5 products by revenue are..."

---

## 10. Automated Testing Commands

```bash
# Run compilation syntax check
.venv/bin/python -m compileall .

# Run full test suite
.venv/bin/pytest -v

# Run targeted security test suite
.venv/bin/pytest -v tests/test_sql_validator.py

# Run benchmark evaluation
.venv/bin/pytest -v tests/test_evaluation.py
```

---

## 11. Security Limitations

1. Read-only SQLite enforcement prevents file corruption, but runaway computations are protected via timeout progress handlers.
2. The table allowlist limits visibility strictly to documented business tables.
3. Parameterized queries protect against SQL injection from user filter values.

---

## 12. Current Implementation Status

| Step | Description | Status | Verification Command |
|---|---|---|---|
| Step 0 | Inspect the environment | **Completed** | Inspected runtimes, venv created |
| Step 1 | Architecture & documentation | **Completed** | Verified decision.md, implementation.md, README.md |
| Step 2 | Scaffolding & configuration | **Completed** | `pytest tests/test_config.py` (6/6 passed) |
| Step 3 | Database & seed data | **Completed** | `pytest tests/test_database.py` (5/5 passed) |
| Step 4 | Dynamic schema inspection | **Completed** | `pytest tests/test_schema_inspector.py` (6/6 passed) |
| Step 5 | Embeddings & ChromaDB | **Completed** | `pytest tests/test_embeddings_retriever.py` (5/5 passed) |
| Step 6 | Structured SQL generation | **Completed** | `pytest tests/test_sql_generator.py` (7/7 passed) |
| Step 7 | SQL validation & security | **Completed** | `pytest tests/test_sql_validator.py` (31/31 passed) |
| Step 8 | Read-only query execution | **Completed** | `pytest tests/test_query_executor.py` (7/7 passed) |
| Step 9 | Agent orchestration | **Completed** | `pytest tests/test_agent.py` (6/6 passed) |
| Step 10 | User interface (Web & CLI) | **Completed** | CLI tested & Streamlit ready |
| Step 11 | Evaluation & benchmark suite | **Completed** | `pytest tests/test_evaluation.py` (100% accuracy, 100% safety) |
| Step 12 | Final audit & documentation | **Completed** | Full suite (74/74 passed), 88% coverage |
