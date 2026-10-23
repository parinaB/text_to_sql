# Architecture and Engineering Decision Record: Text-to-SQL AI Agent

## 1. Project Objective and Scope

The objective of this project is to build a robust, secure, research-ready, and verifiable **Text-to-SQL AI Agent**. The system accepts natural language questions regarding structured business data, leverages ChromaDB to retrieve relevant database schema context and few-shot question-to-SQL examples, employs a configurable Large Language Model (LLM) to generate ANSI SQLite queries, rigorously validates the query AST against a strict security allowlist, executes the query over an enforced read-only SQLite connection, and generates a grounded natural-language explanation of the results.

### In-Scope
- Natural language query understanding for relational business metrics (customers, products, orders, order items).
- Dynamic schema inspection directly from SQLite catalog (`sqlite_master`, PRAGMAs).
- Vector indexing and retrieval of schema semantic descriptions and question-to-SQL exemplars via ChromaDB.
- Multi-tier pluggable embedding support (`nomic-embed-text` via Ollama, cloud embeddings, and offline deterministic embeddings).
- Pydantic-enforced structured generation of SQL, parameters, and assumptions.
- Multi-layered AST-based SQL security verification (single statement, `SELECT` only, table and column allowlist, rejection of data/schema mutation, comment or CTE evasion detection).
- Read-only SQLite query execution using SQLite URI mode `file:...?mode=ro` with execution timeouts and row-count caps.
- Grounded explanation of tabular results and explicit identification of empty results, assumptions, or missing data.
- Automated evaluation harness with diverse query classes (aggregations, temporal filtering, multi-table joins, empty sets, out-of-scope queries, injection attempts).
- Web UI (Streamlit) and interactive CLI.

### Out-of-Scope
- Arbitrary database write operations (INSERT, UPDATE, DELETE).
- Arbitrary DDL operations (ALTER, DROP, CREATE).
- Multi-database cross-platform federation.
- Unconstrained ad-hoc Python code execution.

---

## 2. Functional Requirements

1. **Natural-Language Understanding**: Parse user questions regarding sales, customers, order volumes, revenue, and product catalogs. Handle ambiguity and communicate unanswerable queries gracefully.
2. **Dynamic Schema Inspection**: Introspect table structures, column definitions, data types, primary keys, and foreign keys directly from SQLite metadata.
3. **Semantic Schema & Few-Shot Retrieval**: Index schema metadata and verified question-SQL pairs into ChromaDB. Query-time retrieval provides contextual few-shots to the LLM.
4. **Structured SQL Generation**: Generate SQLite queries bound to Pydantic models containing `sql`, `parameters`, `assumptions`, and `explanation`.
5. **Strict AST Security Policy**: Pass generated SQL through an AST parser before execution. Allow only single `SELECT` statements referencing explicitly permitted tables and columns. Reject all DDL, DML, file attachments, and PRAGMAs.
6. **Isolated Read-Only Execution**: Execute queries via an isolated read-only connection with strict row limits and statement timeouts.
7. **Grounded Natural-Language Interpretation**: Generate explanations derived strictly from executed SQL results without fabricating data.

---

## 3. Non-Functional Requirements

1. **Security**: Defense-in-depth architecture. The LLM has zero direct database access. Read-only connection enforcement prevents writes even if parser validation is bypassed.
2. **Correctness**: Zero tolerance for fabricated data. Unanswerable queries return structured error explanations.
3. **Reproducibility**: All tests and benchmarks run deterministically without requiring external API keys or GPU hardware.
4. **Auditability**: Every query execution has a unique Request ID, logged telemetry, execution time metrics, and row count tracking.
5. **Performance**: Query timeout ceiling of 5000ms. Response payload size capped at 100 rows by default.
6. **Portability**: Operates cleanly on standard laptops running Python 3.11+.

---

## 4. System Architecture

```mermaid
flowchart TD
    User([User Question]) --> Agent[TextToSQLAgent]
    Agent --> Inspector[Dynamic Schema Inspector]
    Inspector --> SchemaContext[(SQLite Catalog)]
    
    Agent --> Retriever[ChromaDB Semantic Retriever]
    Retriever --> PromptBuilder[Prompt Constructor]
    
    SchemaContext --> PromptBuilder
    PromptBuilder --> Generator[LLM SQL Generator]
    
    Generator --> StructuredOutput[Pydantic Structured Output Validation]
    StructuredOutput --> ASTValidator[AST SQL Validator (sqlglot)]
    
    subgraph Security Boundary
        ASTValidator -->|Passed Policy| Executor[Read-Only SQLite Executor]
        ASTValidator -->|Violation / Syntax Error| FeedbackLoop{Retry Policy\nAttempts < 3?}
        FeedbackLoop -->|Yes + Error Diagnostic| Generator
        FeedbackLoop -->|No| RejectHandler[Safe Error Explainer]
    end
    
    Executor --> RawResults[(Tabular Output / Status)]
    RawResults --> Formatter[Answer Formatter & Explainer]
    Formatter --> FinalResponse([User Answer + SQL + Execution Metadata])
```

---

## 5. Component Responsibilities

| Module | Primary Responsibility |
|---|---|
| `config.py` | Validates environment variables, model choices, database paths, and security allowlists. |
| `database.py` | Creates database schema, executes idempotent seed data, and provides read-only SQLite connections. |
| `schema_inspector.py` | Discovers live schema from SQLite metadata (`sqlite_master`, PRAGMAs) and filters by table allowlist. |
| `embeddings.py` | Provides a unified embedding interface supporting Ollama (`nomic-embed-text`), cloud providers, and deterministic testing. |
| `retriever.py` | Indexes and queries ChromaDB vector collections for schema descriptions and few-shot exemplars. |
| `prompts.py` | Constructs system prompts with SQLite dialect specifications, schema context, and few-shot pairs. |
| `sql_generator.py` | Dispatches generation requests to the configured LLM and parses structured Pydantic outputs. |
| `sql_validator.py` | Performs AST parsing (`sqlglot`), checks statement types, enforces table/column allowlists, and blocks mutations. |
| `query_executor.py` | Executes validated SQL against read-only SQLite connections with progress handlers and row limits. |
| `answer_formatter.py` | Synthesizes grounded natural language explanations from execution results and notes assumptions. |
| `agent.py` | Orchestrates the end-to-end pipeline, maintains request tracing, and executes self-healing retry loops. |
| `app.py` | Provides an interactive Streamlit UI and command-line execution interface. |

---

## 6. Technology and Dependency Choices

- **Decision**: Python 3.11 runtime, `sqlglot` for AST parsing, `chromadb` for vector retrieval, `pydantic` v2 for data contracts, and built-in `sqlite3`.
- **Reason**: `sqlglot` is a pure-Python, zero-dependency SQL parser with comprehensive SQLite dialect support, facilitating deep AST inspection without native binary dependencies. Python's built-in `sqlite3` natively supports URI read-only flags (`file:...mode=ro`) and progress handlers.
- **Alternatives considered**:
  - `sqlparse`: Regex-heavy token matching, susceptible to nested query evasion and comment obfuscation. Rejected.
  - `FAISS`: Lacks out-of-the-box persistent document store and metadata filtering. ChromaDB selected for native metadata filtering and persistence.
- **Trade-offs**: ChromaDB brings dependencies like `pydantic` and `numpy`, but provides stable persistence and standard distance metrics.
- **How tested**: Automated compilation and import tests across all modules.

---

## 7. LLM and Embedding Provider Strategy

- **Decision**: Multi-provider pluggable architecture with a mandatory fallback to a deterministic test provider.
- **Reason**: Ensures complete developer flexibility. Users with Ollama can run locally with `nomic-embed-text`. Cloud users can use OpenAI or Gemini. CI/CD test runners and environments without active local servers can execute tests deterministically via the `DeterministicTestProvider`.
- **Alternatives considered**: Hardcoding Ollama or OpenAI. Rejected due to tight coupling and risk of test failures when services are offline.
- **Trade-offs**: Requires building interface adapters, but eliminates brittle external dependencies for automated evaluation.
- **How tested**: Mock and live integration tests verifying vector dimensionality and deterministic query mapping.

---

## 8. Database Schema Strategy

- **Decision**: Four-table relational business schema: `customers`, `products`, `orders`, `order_items`.
- **Reason**: Covers real-world business analytics patterns:
  - Filtering: customer status, order dates.
  - Aggregation: total revenue, order counts, average order value.
  - Joins: customer to order (1:N), order to order_items (1:N), order_items to products (N:1).
  - Empty results: queries for non-existent customers or future date windows.
- **Trade-offs**: Focused schema avoids unnecessary bloat while providing rich relational expressiveness.
- **How tested**: Idempotent database initialization tests; verified row counts and foreign key integrity.

---

## 9. ChromaDB Collection Design

- **Decision**: Two isolated ChromaDB collections:
  1. `schema_collection`: Semantic descriptions of tables and columns.
  2. `few_shot_collection`: Representative natural-language questions mapped to verified SQL queries.
- **Reason**: Decoupling schema knowledge from example queries allows independent indexing, distinct similarity thresholds, and tailored retrieval limits.
- **Alternatives considered**: Single monolithic collection. Rejected due to poor semantic separation and noise in top-k retrieval.
- **How tested**: Ingestion tests verifying metadata keys (`category`, `table_name`) and similarity rankings.

---

## 10. Retrieval and Prompt-Construction Strategy

- **Decision**: Retrieve top-$k$ relevant schema entries and top-$m$ relevant question-SQL pairs; inject them into an immutable prompt template.
- **Reason**: Constrains context window to relevant tables and provides clear behavioral patterns for complex joins and date calculations.
- **Trade-offs**: Fixed $k$ and $m$ balances context precision against LLM context budget.
- **How tested**: Retrieval relevance checks ensuring questions regarding "revenue" retrieve `order_items` and `products`.

---

## 11. SQL Generation Strategy

- **Decision**: Structured output via Pydantic model (`GeneratedSQLResponse`).
- **Reason**: Prevents natural language commentary from contaminating the SQL string. Separates SQL parameters, assumptions, and explanation.
- **Alternatives considered**: Freeform markdown extraction with regex. Rejected as brittle and prone to formatting hallucinations.
- **How tested**: Schema validation tests on JSON outputs across valid and invalid responses.

---

## 12. SQL Validation and Security Model

- **Decision**: Multi-stage AST analysis using `sqlglot`:
  1. Parse query with dialect `sqlite`.
  2. Verify single statement (prohibit multi-statement execution).
  3. Verify expression root is strictly `exp.Select`.
  4. Walk AST to ensure all referenced tables exist in `ALLOWED_TABLES`.
  5. Walk AST to ensure all referenced columns exist in approved table schemas.
  6. Explicitly disallow any mutating AST nodes (`exp.Insert`, `exp.Update`, `exp.Delete`, `exp.Drop`, `exp.Alter`, `exp.Command`, `exp.Pragma`).
  7. Block `ATTACH`, `DETACH`, file I/O functions, and user-defined functions.
- **Reason**: Keyword blacklists can be bypassed by comments (`SELECT/*delete*/...`) or subqueries. AST inspection traverses the semantic syntax tree directly.
- **How tested**: Rigorous security test suite with 25+ malicious, mutating, and evasion queries.

---

## 13. Read-Only Execution Strategy

- **Decision**: Defense-in-depth:
  1. Open SQLite using URI flag `file:<path>?mode=ro`.
  2. Register `set_progress_handler` with instruction threshold to terminate long-running loops.
  3. Apply `LIMIT 100` if no limit is present.
  4. Execute only through parameterized bindings.
- **Reason**: Even if an AST validator has a zero-day bypass, the SQLite C engine will reject disk writes at the OS/file-system level.
- **How tested**: Direct write attempts through read-only connection asserting `sqlite3.OperationalError: attempt to write a readonly database`.

---

## 14. Error Handling and Retry Policy

- **Decision**: Bounded self-healing retry loop (maximum 2 retries, 3 total attempts).
- **Reason**: When an LLM generates a query with a syntax error or a disallowed column, feeding the exact parser/executor diagnostic back to the LLM allows self-correction.
- **Alternatives considered**: Infinite retry or zero retry. Zero retry causes brittle failures; infinite retry risks infinite loops and excessive latency.
- **How tested**: Mock tests injecting syntax errors on turn 1 and asserting successful recovery on turn 2.

---

## 15. Testing Strategy

- **Decision**: Multi-layer pyramid:
  - Unit tests for database seeding, AST validator, query executor, retriever, prompt builder.
  - Integration tests for end-to-end agent orchestration.
  - Security tests targeting SQL injection, DDL/DML, and evasion patterns.
  - Evaluation suite running 25 benchmark queries.
- **Reason**: Validates isolated logic and full system interactions independently.
- **How tested**: Executed via `pytest` with coverage tracking.

---

## 16. Evaluation Metrics

- **SQL Execution Accuracy**: Percentage of questions producing valid, executable SQL.
- **Result Correctness**: Ground-truth comparison of returned rows/aggregates against verified baseline answers.
- **Safety Rejection Rate**: 100% rejection required for unauthorized or mutating queries.
- **Latency**: Mean and P95 latency per question.

---

## 17. Logging and Observability

- **Decision**: Standard library `logging` with structured formatting including timestamp, logger name, log level, Request ID, and component name.
- **Reason**: Zero extra dependencies, high throughput, and easily piped to file or stdout.
- **Trade-offs**: Secrets and database credentials must be scrubbed before logging.
- **How tested**: Verifying presence of Request ID across logs during test runs.

---

## 18. Configuration and Environment Setup

- **Decision**: Centralized Pydantic `BaseSettings` reading from `.env` or system environment.
- **Reason**: Type safety, default value enforcement, and automated validation on application startup.
- **How tested**: Unit tests asserting default values and validation failures on invalid settings.

---

## 19. Known Limitations and Risks

1. Complex business logic requiring domain knowledge outside the database schema may require explicit user clarification.
2. Dialect differences: SQLite SQL syntax has nuances (e.g. `strftime` for dates rather than `DATEADD` or `INTERVAL`).
3. Local hardware constraints: Local LLMs require sufficient RAM/VRAM; fallback provider mitigates offline/resource-constrained runs.

---

## 20. Future Improvements

1. Support for additional SQL dialects (PostgreSQL, BigQuery, DuckDB) via dialect adapters.
2. Semantic caching of verified SQL queries to minimize LLM latency and cost for repeated queries.
3. Interactive user clarification dialog when ambiguity score exceeds a configurable threshold.
