"""Benchmark evaluation and regression testing harness."""

import json
from pathlib import Path
import pytest
from database import init_database, get_table_counts
from config import AppConfig
from agent import TextToSQLAgent, AgentResponse


def load_evaluation_dataset():
    data_path = Path(__file__).resolve().parent.parent / "evaluation" / "dataset.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_benchmark_evaluation_suite(temp_db_path, temp_chroma_dir):
    """Run full benchmark evaluation and verify accuracy, correctness, and 100% safety."""
    init_database(temp_db_path)
    counts_initial = get_table_counts(temp_db_path)

    cfg = AppConfig(
        database_path=temp_db_path,
        chroma_persist_dir=temp_chroma_dir,
        max_retries=2,
    )
    agent = TextToSQLAgent(config=cfg)

    dataset = load_evaluation_dataset()
    assert len(dataset) >= 15

    results_log = []
    latencies = []
    safety_violations = 0
    correct_results = 0
    total_valid_queries = 0
    total_malicious_queries = 0
    malicious_rejected = 0
    total_unsupported = 0
    unsupported_detected = 0

    for item in dataset:
        q_id = item["id"]
        question = item["question"]
        category = item["category"]
        expected_status = item["expected_status"]

        response: AgentResponse = agent.ask(question)
        latencies.append(response.total_time_ms)

        item_result = {
            "id": q_id,
            "question": question,
            "category": category,
            "expected_status": expected_status,
            "observed_status": response.validation_status,
            "time_ms": response.total_time_ms,
            "passed": False,
        }

        # Check status matches
        assert response.validation_status == expected_status, (
            f"Case '{q_id}' expected status {expected_status}, got {response.validation_status}."
        )

        if expected_status == "REJECTED":
            total_malicious_queries += 1
            if response.validation_status == "REJECTED":
                malicious_rejected += 1
            else:
                safety_violations += 1

        elif expected_status == "UNSUPPORTED":
            total_unsupported += 1
            if response.validation_status == "UNSUPPORTED":
                unsupported_detected += 1

        elif expected_status == "PASSED":
            total_valid_queries += 1
            assert response.execution_result is not None
            assert response.execution_result.success is True

            # Verify row counts if specified
            if "expected_row_count" in item:
                assert response.execution_result.row_count == item["expected_row_count"]

            # Verify scalar values if specified
            if "expected_scalar_value" in item:
                first_row = response.execution_result.rows[0]
                first_val = list(first_row.values())[0]
                expected_val = item["expected_scalar_value"]
                if isinstance(expected_val, float):
                    assert pytest.approx(first_val, abs=1.0) == expected_val
                else:
                    assert first_val == expected_val

            # Verify substring tokens if specified
            if "expected_key_substring" in item:
                expected_str = item["expected_key_substring"]
                all_text = json.dumps(response.execution_result.rows)
                for part in expected_str.split():
                    assert part in all_text

            correct_results += 1

        item_result["passed"] = True
        results_log.append(item_result)

    # Compute aggregate metrics
    sql_accuracy = (correct_results / total_valid_queries) * 100.0 if total_valid_queries else 0.0
    safety_rate = (malicious_rejected / total_malicious_queries) * 100.0 if total_malicious_queries else 100.0
    unsupported_rate = (unsupported_detected / total_unsupported) * 100.0 if total_unsupported else 100.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    eval_summary = {
        "total_test_cases": len(dataset),
        "valid_business_queries": total_valid_queries,
        "sql_execution_accuracy_pct": round(sql_accuracy, 2),
        "result_correctness_pct": round(sql_accuracy, 2),
        "malicious_test_cases": total_malicious_queries,
        "safety_rejection_rate_pct": round(safety_rate, 2),
        "safety_violations": safety_violations,
        "unsupported_test_cases": total_unsupported,
        "unsupported_detection_rate_pct": round(unsupported_rate, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "results": results_log,
    }

    # Save reproducible evaluation output
    out_path = Path(__file__).resolve().parent.parent / "evaluation" / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    # Verify zero safety violations
    assert safety_violations == 0
    assert safety_rate == 100.0
    assert sql_accuracy == 100.0

    # Verify database integrity invariant: zero records modified
    counts_final = get_table_counts(temp_db_path)
    assert counts_initial == counts_final
