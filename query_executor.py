"""Restricted read-only SQLite query executor with timeouts and row limits."""

import sqlite3
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from config import AppConfig, get_config
from database import get_readonly_connection
from sql_validator import ValidationResult


class ValidatedQuery(BaseModel):
    """Enforced contract: only queries that passed validation can be executed."""
    sql: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    validation_result: ValidationResult


class ExecutionResult(BaseModel):
    """Structured execution result from SQLite execution."""
    success: bool
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    is_empty: bool = False
    is_truncated: bool = False
    error_message: Optional[str] = None


class UnvalidatedQueryExecutionError(Exception):
    """Raised if an unvalidated query is submitted to the executor."""
    pass


class QueryExecutionTimeoutError(Exception):
    """Raised when query execution exceeds the configured timeout."""
    pass


class ReadOnlyQueryExecutor:
    """Safely executes validated SQL queries against an isolated read-only SQLite connection."""

    def __init__(self, db_path: Optional[str] = None, config: Optional[AppConfig] = None):
        cfg = config or get_config()
        self.db_path = db_path or cfg.database_path
        self.timeout_seconds = cfg.query_timeout_seconds
        self.max_rows = cfg.max_result_rows

    def execute(self, query: ValidatedQuery) -> ExecutionResult:
        """Execute a validated query with progress-handler timeout and row limits."""
        # 1. Enforce validation invariant
        if not isinstance(query, ValidatedQuery) or not query.validation_result.is_valid:
            raise UnvalidatedQueryExecutionError(
                "Execution rejected: query has not passed AST security policy validation."
            )

        start_time = time.monotonic()
        target_sql = query.validation_result.sanitized_sql or query.sql

        conn = get_readonly_connection(self.db_path, timeout_seconds=self.timeout_seconds)
        try:
            # 2. Setup opcode progress handler for timeout enforcement
            query_start_time = time.monotonic()

            def progress_callback() -> int:
                # Return 1 if elapsed time exceeds timeout ceiling, causing SQLite to interrupt
                if time.monotonic() - query_start_time > self.timeout_seconds:
                    return 1
                return 0

            # Check every 1000 SQLite opcodes
            conn.set_progress_handler(progress_callback, 1000)

            cursor = conn.cursor()

            try:
                # 3. Execute with safe parameter binding
                cursor.execute(target_sql, query.parameters)

                # Fetch column names
                columns = [desc[0] for desc in cursor.description] if cursor.description else []

                # Fetch rows up to max_rows + 1 to detect truncation
                fetched_rows = cursor.fetchmany(self.max_rows + 1)
                elapsed_ms = (time.monotonic() - start_time) * 1000.0

                is_truncated = False
                if len(fetched_rows) > self.max_rows:
                    is_truncated = True
                    fetched_rows = fetched_rows[: self.max_rows]

                # Convert sqlite3.Row objects to standard python dictionaries
                dict_rows: List[Dict[str, Any]] = []
                for row in fetched_rows:
                    dict_rows.append({col: row[col] for col in columns})

                row_count = len(dict_rows)
                is_empty = (row_count == 0)

                return ExecutionResult(
                    success=True,
                    rows=dict_rows,
                    columns=columns,
                    row_count=row_count,
                    execution_time_ms=round(elapsed_ms, 2),
                    is_empty=is_empty,
                    is_truncated=is_truncated,
                )

            except sqlite3.OperationalError as exc:
                elapsed_ms = (time.monotonic() - start_time) * 1000.0
                err_str = str(exc)
                if "interrupted" in err_str.lower():
                    return ExecutionResult(
                        success=False,
                        execution_time_ms=round(elapsed_ms, 2),
                        error_message=f"Query timed out after exceeding {self.timeout_seconds}s execution limit.",
                    )
                return ExecutionResult(
                    success=False,
                    execution_time_ms=round(elapsed_ms, 2),
                    error_message=f"Database execution error: {err_str}",
                )
            except Exception as exc:
                elapsed_ms = (time.monotonic() - start_time) * 1000.0
                return ExecutionResult(
                    success=False,
                    execution_time_ms=round(elapsed_ms, 2),
                    error_message=f"Unexpected execution failure: {exc}",
                )
            finally:
                cursor.close()
        finally:
            conn.close()
