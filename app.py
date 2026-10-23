"""Interactive Streamlit Web UI and CLI entry point for the Text-to-SQL AI Agent."""

import argparse
import sys
from typing import Optional

from agent import TextToSQLAgent, AgentResponse
from config import get_config
from database import get_table_counts


def run_cli(question: str) -> None:
    """Run agent in CLI mode and print structured output."""
    agent = TextToSQLAgent()
    print("\n" + "=" * 70)
    print("TEXT-TO-SQL AGENT: CLI EXECUTION")
    print("=" * 70)
    print(f"Question: {question}\n")

    response: AgentResponse = agent.ask(question)

    print(f"Request ID:        {response.request_id}")
    print(f"Validation Status: {response.validation_status}")
    print(f"Attempts:          {response.attempts}")
    print(f"Execution Time:    {response.total_time_ms} ms")
    print("-" * 70)

    if response.sql:
        print("Generated SQL Query:")
        print(response.sql)
        print("-" * 70)

    if response.assumptions:
        print("Assumptions Applied:")
        for a in response.assumptions:
            print(f"  - {a}")
        print("-" * 70)

    if response.execution_result and response.execution_result.rows:
        print(f"Query Results ({response.execution_result.row_count} rows):")
        cols = response.execution_result.columns
        header = " | ".join(cols)
        print(header)
        print("-" * len(header))
        for row in response.execution_result.rows[:5]:
            print(" | ".join(str(row.get(c, "")) for c in cols))
        if response.execution_result.is_truncated:
            print("  *(Truncated to max limit)*")
        print("-" * 70)

    print("Natural-Language Answer:")
    print(response.answer)
    print("=" * 70 + "\n")


def run_streamlit() -> None:
    """Run interactive Streamlit user interface."""
    import streamlit as st

    st.set_page_config(
        page_title="Text-to-SQL AI Agent",
        page_icon="🔍",
        layout="wide",
    )

    st.title("🔍 Text-to-SQL AI Agent")
    st.caption("Convert natural language inquiries into safe, verified, read-only SQLite SQL queries.")

    cfg = get_config()

    # Sidebar: System status and telemetry
    with st.sidebar:
        st.header("⚙️ System Status")
        st.write(f"**LLM Provider:** `{cfg.llm_provider}`")
        st.write(f"**Embedding Provider:** `{cfg.embedding_provider}`")
        st.write(f"**Database:** `{cfg.database_path}`")
        st.write(f"**Max Retries:** `{cfg.max_retries}`")
        st.write(f"**Timeout Ceiling:** `{cfg.query_timeout_seconds}s`")

        st.divider()
        st.subheader("📊 Database Records")
        try:
            counts = get_table_counts(cfg.database_path)
            for tbl, cnt in counts.items():
                st.write(f"- `{tbl}`: {cnt:,} rows")
        except Exception as exc:
            st.error(f"Database error: {exc}")

        st.divider()
        st.subheader("💡 Example Questions")
        examples = [
            "How many orders did we receive in October 2026?",
            "What was our total revenue in September 2026?",
            "Which 5 products generated the most revenue?",
            "What is the average order value?",
            "How many orders did each customer place?",
            "Which products have never been ordered?",
            "What is our customer satisfaction CSAT score?",
            "Drop all tables now",
        ]
        for ex in examples:
            if st.button(ex, key=f"btn_{ex[:15]}", use_container_width=True):
                st.session_state["query_input"] = ex

    # Main query interface
    default_val = st.session_state.get("query_input", "How many orders did we receive in October 2026?")
    user_query = st.text_input("Enter your business question:", value=default_val)

    if st.button("Submit Query", type="primary", use_container_width=False):
        if not user_query.strip():
            st.warning("Please enter a question.")
            return

        with st.spinner("Analyzing question, retrieving schema, and validating query..."):
            agent = TextToSQLAgent()
            resp: AgentResponse = agent.ask(user_query)

        # Status badge
        if resp.validation_status == "PASSED":
            st.success(f"Query Processed Successfully ({resp.total_time_ms} ms)")
        elif resp.validation_status == "UNSUPPORTED":
            st.info(f"Question Unsupported by Schema ({resp.total_time_ms} ms)")
        elif resp.validation_status == "REJECTED":
            st.error(f"Query Rejected by Security Policy ({resp.total_time_ms} ms)")
        else:
            st.error(f"System Error Encountered ({resp.total_time_ms} ms)")

        # Main response card
        st.markdown("### 💬 Grounded Explanation")
        st.markdown(resp.answer)

        # Tabular details
        tab1, tab2, tab3 = st.tabs(["SQL & Parameters", "Data Results", "Audit Telemetry"])

        with tab1:
            if resp.sql:
                st.code(resp.sql, language="sql")
                if resp.parameters:
                    st.json(resp.parameters)
            else:
                st.write("No SQL generated.")

        with tab2:
            if resp.execution_result and resp.execution_result.rows:
                st.dataframe(resp.execution_result.rows, use_container_width=True)
            elif resp.execution_result and resp.execution_result.is_empty:
                st.info("Query returned 0 records.")
            else:
                st.write("No data records available.")

        with tab3:
            st.json({
                "request_id": resp.request_id,
                "validation_status": resp.validation_status,
                "attempts": resp.attempts,
                "total_time_ms": resp.total_time_ms,
                "assumptions": resp.assumptions,
            })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Text-to-SQL AI Agent")
    parser.add_argument("--cli", type=str, help="Run single question in CLI mode")
    args, unknown = parser.parse_known_args()

    if args.cli:
        run_cli(args.cli)
    else:
        # Check if launched via Streamlit runner
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            if get_script_run_ctx() is not None:
                run_streamlit()
            else:
                # Direct python execution defaults to CLI demonstration if not inside streamlit
                run_cli("How many orders did we receive in October 2026?")
        except ImportError:
            run_cli("How many orders did we receive in October 2026?")
