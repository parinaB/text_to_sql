"""System prompts and prompt construction for SQL generation and explanation."""

from typing import Optional, Tuple


SQL_GENERATION_SYSTEM_PROMPT = """You are a senior SQLite database engineer and SQL expert.
Your job is to convert natural-language business questions into safe, accurate, read-only SQLite SQL queries.

### STRICT RULES:
1. DIALECT: Generate ANSI SQLite syntax only.
   - For dates, use standard ISO 'YYYY-MM-DD' strings and SQLite date functions like `strftime()` or direct string comparisons (e.g., `order_date >= '2026-10-01' AND order_date <= '2026-10-31'`).
2. SAFETY: You must ONLY generate `SELECT` queries.
   - NEVER generate `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `DETACH`, or `PRAGMA`.
   - Never reference tables or columns not present in the provided schema.
3. UNSUPPORTED QUESTIONS:
   - If the database schema cannot answer the question (e.g., asking for data that doesn't exist such as stock prices, employee salaries, customer passwords), you MUST set "is_supported": false, "sql": "", and explain why in "explanation".
   - Do NOT invent or hallucinate non-existent tables or columns.
4. STRUCTURED OUTPUT:
   - You MUST respond with a valid JSON object matching this schema:
   {
     "sql": "SELECT ...",
     "parameters": {},
     "assumptions": ["Assumption 1", "Assumption 2"],
     "explanation": "Explanation of how the query answers the question",
     "is_supported": true
   }
   - Do NOT wrap JSON in additional conversational text.
"""


def build_sql_generation_prompt(
    question: str,
    schema_ddl: str,
    retrieved_context_str: str,
    error_feedback: Optional[str] = None,
) -> Tuple[str, str]:
    """Construct system prompt and user prompt for SQL generation."""
    user_parts = [
        "### Database Schema (DDL):",
        schema_ddl,
        "",
    ]

    if retrieved_context_str.strip():
        user_parts.append(retrieved_context_str.strip())
        user_parts.append("")

    if error_feedback:
        user_parts.append("### CRITICAL: PREVIOUS ATTEMPT FAILED WITH ERROR:")
        user_parts.append(f"Error Diagnostic: {error_feedback}")
        user_parts.append("Please analyze the schema carefully, correct the error, and generate a valid SQLite query.")
        user_parts.append("")

    user_parts.append(f"### User Question:\n\"{question.strip()}\"")
    user_parts.append("\nReturn strictly the JSON object:")

    return SQL_GENERATION_SYSTEM_PROMPT, "\n".join(user_parts)
