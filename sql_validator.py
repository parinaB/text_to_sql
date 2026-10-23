"""Multi-layered AST-based SQL security policy validator."""

import re
from typing import List, Optional, Set
import sqlglot
from sqlglot import exp
from pydantic import BaseModel, Field

from config import AppConfig, get_config
from schema_inspector import DatabaseSchema


class ValidationResult(BaseModel):
    """Result of SQL safety and policy validation."""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_sql: Optional[str] = None
    tables_accessed: Set[str] = Field(default_factory=set)


# Prohibited AST node types
MUTATING_EXPRESSION_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Pragma,
    exp.LoadData,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Set,
)

# Prohibited function calls
DANGEROUS_FUNCTIONS = {
    "load_extension",
    "writefile",
    "readfile",
    "eval",
    "system",
    "exec",
    "shell",
}


class SQLValidator:
    """Rigorous AST-based SQL security validator for SQLite."""

    def __init__(
        self,
        allowed_tables: Optional[Set[str]] = None,
        schema: Optional[DatabaseSchema] = None,
    ):
        cfg = get_config()
        raw_allowed = allowed_tables or cfg.allowed_tables
        self.allowed_tables = {t.lower() for t in raw_allowed}
        self.schema = schema

    def validate(
        self,
        sql: str,
        schema: Optional[DatabaseSchema] = None,
    ) -> ValidationResult:
        """Validate that SQL is a safe, single, read-only SELECT referencing only allowed tables and columns."""
        clean_sql = sql.strip()
        if not clean_sql:
            return ValidationResult(is_valid=False, error_message="Empty query string is not permitted.")

        # Check for prohibited command patterns that some parsers might treat as comments or commands
        forbidden_keywords = [
            r"\bATTACH\b",
            r"\bDETACH\b",
            r"\bPRAGMA\b",
            r"\bVACUUM\b",
            r"\bREINDEX\b",
        ]
        for pattern in forbidden_keywords:
            if re.search(pattern, clean_sql, re.IGNORECASE):
                matched = re.search(pattern, clean_sql, re.IGNORECASE).group(0)
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Disallowed command keyword '{matched.upper()}' detected in SQL.",
                )

        # 1. Parse using sqlglot with SQLite dialect
        try:
            expressions = sqlglot.parse(clean_sql, read="sqlite")
        except Exception as exc:
            return ValidationResult(
                is_valid=False,
                error_message=f"SQL syntax error: Failed to parse query into SQLite AST: {exc}",
            )

        if not expressions:
            return ValidationResult(is_valid=False, error_message="Query parsed into zero executable statements.")

        # 2. Strict single statement check
        if len(expressions) > 1:
            return ValidationResult(
                is_valid=False,
                error_message=f"Multiple SQL statements ({len(expressions)}) are strictly prohibited; exactly one statement is permitted.",
            )

        root = expressions[0]

        # 3. Root statement type verification
        # Must be a Select or set operation (UNION, INTERSECT, EXCEPT), including WITH ... SELECT CTEs
        if not isinstance(root, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
            return ValidationResult(
                is_valid=False,
                error_message=f"Prohibited statement type: expected 'SELECT' query, got '{root.key.upper()}'.",
            )

        # 4. Deep AST traversal for any mutating or prohibited nodes anywhere in tree (including subqueries and CTEs)
        for node in root.walk():
            if isinstance(node, MUTATING_EXPRESSION_TYPES):
                node_type = type(node).__name__.replace("exp.", "")
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Prohibited mutating operation detected in AST: '{node_type}'.",
                )

            # Check for dangerous functions
            if isinstance(node, (exp.Anonymous, exp.Func)):
                func_name = (node.name or "").lower()
                if func_name in DANGEROUS_FUNCTIONS:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Prohibited dangerous function detected: '{func_name}()'.",
                    )

        # 5. Extract CTE aliases to exclude them from physical table verification
        cte_names = {c.alias.lower() for c in root.find_all(exp.CTE) if c.alias}

        # 6. Physical table allowlist validation
        accessed_tables: Set[str] = set()
        for tbl in root.find_all(exp.Table):
            if tbl.name:
                t_name = tbl.name.lower()
                if t_name not in cte_names:
                    accessed_tables.add(t_name)

        if not accessed_tables:
            # Queries without FROM like "SELECT 1;" or "SELECT datetime('now');"
            pass
        else:
            unauthorized = accessed_tables - self.allowed_tables
            if unauthorized:
                sorted_unauth = sorted(list(unauthorized))
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Access to unauthorized table(s) prohibited: {sorted_unauth}. Allowed tables: {sorted(list(self.allowed_tables))}.",
                    tables_accessed=accessed_tables,
                )

        # 7. Column validation against schema if provided
        active_schema = schema or self.schema
        if active_schema:
            for col in root.find_all(exp.Column):
                col_name = col.name
                table_qual = col.table
                if table_qual:
                    tbl_lower = table_qual.lower()
                    if tbl_lower in self.allowed_tables and not active_schema.is_valid_column(tbl_lower, col_name):
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Column '{col_name}' does not exist on table '{tbl_lower}'.",
                            tables_accessed=accessed_tables,
                        )

        # Generate canonical sanitized SQL
        sanitized = root.sql(dialect="sqlite")

        return ValidationResult(
            is_valid=True,
            sanitized_sql=sanitized,
            tables_accessed=accessed_tables,
        )
