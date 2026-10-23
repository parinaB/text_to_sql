"""Natural-language answer formatter for Text-to-SQL results."""

from typing import Any, Dict, List, Optional
from query_executor import ExecutionResult


class AnswerFormatter:
    """Formats grounded, plain-English explanations from execution results."""

    def format_unsupported(self, question: str, explanation: str) -> str:
        """Format response for out-of-scope or unanswerable queries."""
        reason = explanation or "The database schema does not contain the information required to answer this inquiry."
        return f"I cannot answer this question from the available database records. {reason}"

    def format_validation_error(self, question: str, error_message: str) -> str:
        """Format response for queries rejected by security policy."""
        return (
            f"The generated query could not be executed because it violated security or schema constraints: "
            f"{error_message}"
        )

    def format_execution_error(self, error_message: str) -> str:
        """Format response when query execution encounters a runtime error."""
        return f"A database execution error occurred: {error_message}"

    def format_empty_result(self, question: str, assumptions: List[str]) -> str:
        """Format response when query succeeded but returned zero rows."""
        text = "The query executed successfully, but found 0 matching records in the database."
        if assumptions:
            text += f" (Assumptions applied: {'; '.join(assumptions)})"
        return text

    def format_success(
        self,
        question: str,
        result: ExecutionResult,
        assumptions: List[str],
        explanation: str,
    ) -> str:
        """Format response for successful queries with rows."""
        rows = result.rows
        columns = result.columns
        row_count = result.row_count

        parts: List[str] = []

        # 1. Single scalar result (e.g. COUNT(*), SUM(...), AVG(...))
        if row_count == 1 and len(columns) == 1:
            val = rows[0][columns[0]]
            col_name = columns[0]
            # Currency formatting if numeric and represents financial amount (not count)
            is_money = any(m in col_name.lower() for m in ["revenue", "price", "amount", "cost", "spend", "value"]) and not any(c in col_name.lower() for c in ["count", "cnt", "orders", "quantity", "num"])
            if isinstance(val, (int, float)) and is_money:
                val_str = f"${val:,.2f}" if isinstance(val, float) else f"${val:,}"
            elif isinstance(val, float):
                val_str = f"{val:,.2f}"
            else:
                val_str = str(val)

            parts.append(f"Result: {val_str}.")

        # 2. Multi-row tabular output
        else:
            parts.append(f"Retrieved {row_count} record{'s' if row_count != 1 else ''}:")
            # Build markdown table preview
            header = "| " + " | ".join(columns) + " |"
            sep = "| " + " | ".join(["---"] * len(columns)) + " |"
            parts.append(header)
            parts.append(sep)
            for row in rows[:10]:
                row_vals = [str(row.get(col, "")) for col in columns]
                parts.append("| " + " | ".join(row_vals) + " |")

            if result.is_truncated:
                parts.append(f"\n*(Note: Results truncated to {row_count} rows)*")

        if explanation:
            parts.append(f"\n{explanation}")

        if assumptions:
            parts.append(f"\n**Assumptions:**\n" + "\n".join(f"- {a}" for a in assumptions))

        return "\n".join(parts)
