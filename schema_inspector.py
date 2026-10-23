"""Dynamic database schema inspection directly from SQLite metadata."""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from database import get_readonly_connection


class ColumnInfo(BaseModel):
    """Metadata describing a database column."""
    name: str
    data_type: str
    is_primary_key: bool = False
    is_nullable: bool = True
    default_value: Optional[str] = None


class ForeignKeyInfo(BaseModel):
    """Metadata describing a foreign key relationship."""
    column: str
    foreign_table: str
    foreign_column: str


class TableInfo(BaseModel):
    """Metadata describing a database table."""
    name: str
    columns: List[ColumnInfo] = Field(default_factory=list)
    primary_keys: List[str] = Field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = Field(default_factory=list)

    @property
    def column_names(self) -> List[str]:
        return [col.name for col in self.columns]

    def has_column(self, col_name: str) -> bool:
        return col_name.lower() in [col.name.lower() for col in self.columns]


class DatabaseSchema(BaseModel):
    """Complete dynamic database schema context."""
    tables: Dict[str, TableInfo] = Field(default_factory=dict)

    def get_table(self, table_name: str) -> Optional[TableInfo]:
        return self.tables.get(table_name.lower())

    def get_table_names(self) -> List[str]:
        return list(self.tables.keys())

    def is_valid_table(self, table_name: str) -> bool:
        return table_name.lower() in self.tables

    def is_valid_column(self, table_name: str, column_name: str) -> bool:
        tbl = self.get_table(table_name)
        if not tbl:
            return False
        return tbl.has_column(column_name)

    def to_markdown(self) -> str:
        """Render a structured markdown summary of the schema for LLM prompting."""
        if not self.tables:
            return "No tables available."

        lines = ["# Database Schema Information\n"]
        for tbl_name, tbl in sorted(self.tables.items()):
            lines.append(f"### Table: `{tbl.name}`")
            lines.append("| Column | Type | PK | Nullable | Notes |")
            lines.append("|---|---|---|---|---|")
            for col in tbl.columns:
                pk_str = "✓" if col.is_primary_key else ""
                null_str = "YES" if col.is_nullable else "NO"
                notes = []
                for fk in tbl.foreign_keys:
                    if fk.column.lower() == col.name.lower():
                        notes.append(f"FK -> `{fk.foreign_table}.{fk.foreign_column}`")
                notes_str = "; ".join(notes)
                lines.append(f"| `{col.name}` | {col.data_type} | {pk_str} | {null_str} | {notes_str} |")

            if tbl.foreign_keys:
                lines.append("\n**Foreign Key Relationships:**")
                for fk in tbl.foreign_keys:
                    lines.append(f"- `{tbl.name}.{fk.column}` REFERENCES `{fk.foreign_table}({fk.foreign_column})`")
            lines.append("")

        return "\n".join(lines)

    def to_ddl_summary(self) -> str:
        """Generate concise DDL schema definitions for prompt injection."""
        ddl_parts = []
        for tbl_name, tbl in sorted(self.tables.items()):
            col_defs = []
            for col in tbl.columns:
                def_str = f"    {col.name} {col.data_type}"
                if col.is_primary_key and len(tbl.primary_keys) == 1:
                    def_str += " PRIMARY KEY"
                if not col.is_nullable:
                    def_str += " NOT NULL"
                col_defs.append(def_str)

            for fk in tbl.foreign_keys:
                col_defs.append(f"    FOREIGN KEY ({fk.column}) REFERENCES {fk.foreign_table}({fk.foreign_column})")

            ddl_parts.append(f"CREATE TABLE {tbl.name} (\n" + ",\n".join(col_defs) + "\n);")
        return "\n\n".join(ddl_parts)


def inspect_database(
    db_path: str = "business.db",
    allowed_tables: Optional[Set[str]] = None,
) -> DatabaseSchema:
    """Inspect SQLite database and return dynamic schema, excluding unauthorized tables."""
    path_obj = Path(db_path).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"Database file does not exist: {path_obj}")

    conn = get_readonly_connection(str(path_obj))
    try:
        cursor = conn.cursor()

        # Discover all user tables (exclude internal sqlite_ tables)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        all_tables = [row[0] for row in cursor.fetchall()]

        # Filter by allowed tables if specified
        if allowed_tables is not None:
            normalized_allowed = {t.lower() for t in allowed_tables}
            active_tables = [t for t in all_tables if t.lower() in normalized_allowed]
        else:
            active_tables = all_tables

        schema = DatabaseSchema()

        for tbl_name in active_tables:
            # Query column details via PRAGMA table_info
            cursor.execute(f'PRAGMA table_info("{tbl_name}")')
            col_rows = cursor.fetchall()

            columns: List[ColumnInfo] = []
            primary_keys: List[str] = []

            for row in col_rows:
                # cid, name, type, notnull, dflt_value, pk
                col_name = row[1]
                data_type = row[2] or "TEXT"
                not_null = bool(row[3])
                default_val = row[4]
                is_pk = bool(row[5])

                if is_pk:
                    primary_keys.append(col_name)

                columns.append(
                    ColumnInfo(
                        name=col_name,
                        data_type=data_type.upper(),
                        is_primary_key=is_pk,
                        is_nullable=not not_null,
                        default_value=str(default_val) if default_val is not None else None,
                    )
                )

            # Query foreign key details via PRAGMA foreign_key_list
            cursor.execute(f'PRAGMA foreign_key_list("{tbl_name}")')
            fk_rows = cursor.fetchall()
            foreign_keys: List[ForeignKeyInfo] = []

            for fk in fk_rows:
                # id, seq, table, from, to, on_update, on_delete, match
                foreign_table = fk[2]
                from_col = fk[3]
                to_col = fk[4]

                # Only include FK relationship if referenced table is also allowed
                if allowed_tables is None or foreign_table.lower() in normalized_allowed:
                    foreign_keys.append(
                        ForeignKeyInfo(
                            column=from_col,
                            foreign_table=foreign_table,
                            foreign_column=to_col,
                        )
                    )

            schema.tables[tbl_name.lower()] = TableInfo(
                name=tbl_name,
                columns=columns,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
            )

        return schema
    finally:
        conn.close()
