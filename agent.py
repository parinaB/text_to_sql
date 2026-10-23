"""End-to-end Text-to-SQL Agent orchestrator with request tracing and self-healing retries."""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from config import AppConfig, get_config
from schema_inspector import DatabaseSchema, inspect_database
from retriever import RetrievedContext, retrieve_context
from sql_generator import (
    SQLGenerator,
    GeneratedSQLResponse,
    get_llm_client,
    LLMServiceUnavailableError,
    MalformedLLMResponseError,
)
from sql_validator import SQLValidator, ValidationResult
from query_executor import (
    ReadOnlyQueryExecutor,
    ValidatedQuery,
    ExecutionResult,
)
from answer_formatter import AnswerFormatter


logger = logging.getLogger("TextToSQLAgent")


class AgentResponse(BaseModel):
    """Unified response object returned by the Text-to-SQL Agent."""
    request_id: str
    question: str
    sql: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    validation_status: str  # "PASSED", "REJECTED", "UNSUPPORTED", "ERROR"
    execution_result: Optional[ExecutionResult] = None
    answer: str
    attempts: int = 1
    total_time_ms: float = 0.0


class TextToSQLAgent:
    """Master orchestrator for natural language business question answering."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        generator: Optional[SQLGenerator] = None,
        validator: Optional[SQLValidator] = None,
        executor: Optional[ReadOnlyQueryExecutor] = None,
        formatter: Optional[AnswerFormatter] = None,
    ):
        self.config = config or get_config()
        self.generator = generator or SQLGenerator(config=self.config)
        self.validator = validator or SQLValidator(allowed_tables=self.config.allowed_tables)
        self.executor = executor or ReadOnlyQueryExecutor(config=self.config)
        self.formatter = formatter or AnswerFormatter()

    def ask(self, question: str) -> AgentResponse:
        """Process a natural language question through retrieval, generation, validation, execution, and explanation."""
        start_time = time.monotonic()
        request_id = f"req_{uuid.uuid4().hex[:8]}"

        logger.info(f"[{request_id}] Starting query processing: '{question}'")

        # 1. Dynamic schema inspection
        try:
            schema = inspect_database(
                db_path=self.config.database_path,
                allowed_tables=self.config.allowed_tables,
            )
        except Exception as exc:
            logger.error(f"[{request_id}] Schema inspection failed: {exc}")
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            return AgentResponse(
                request_id=request_id,
                question=question,
                validation_status="ERROR",
                answer=f"System error: could not inspect database schema: {exc}",
                attempts=0,
                total_time_ms=round(elapsed_ms, 2),
            )

        # 2. Semantic retrieval from ChromaDB
        try:
            context = retrieve_context(
                question=question,
                chroma_dir=self.config.chroma_persist_dir,
            )
        except Exception as exc:
            logger.warning(f"[{request_id}] ChromaDB retrieval error, continuing with schema only: {exc}")
            context = RetrievedContext(question=question)

        # 3. Self-healing Generation & Validation Loop
        attempt = 0
        max_attempts = 1 + self.config.max_retries
        error_feedback: Optional[str] = None
        gen_response: Optional[GeneratedSQLResponse] = None
        val_result: Optional[ValidationResult] = None

        while attempt < max_attempts:
            attempt += 1
            logger.info(f"[{request_id}] Generation attempt {attempt}/{max_attempts}")

            # Call LLM generator
            try:
                gen_response = self.generator.generate_sql(
                    question=question,
                    schema=schema,
                    retrieved_context=context,
                    error_feedback=error_feedback,
                )
            except LLMServiceUnavailableError as exc:
                logger.error(f"[{request_id}] LLM service unreachable: {exc}")
                elapsed_ms = (time.monotonic() - start_time) * 1000.0
                return AgentResponse(
                    request_id=request_id,
                    question=question,
                    validation_status="ERROR",
                    answer=str(exc),
                    attempts=attempt,
                    total_time_ms=round(elapsed_ms, 2),
                )
            except MalformedLLMResponseError as exc:
                logger.warning(f"[{request_id}] Malformed LLM response on attempt {attempt}: {exc}")
                error_feedback = f"Response was not valid JSON matching schema: {exc}"
                continue

            # Check if question is out-of-scope or unsupported
            if not gen_response.is_supported:
                logger.info(f"[{request_id}] Question identified as unsupported.")
                elapsed_ms = (time.monotonic() - start_time) * 1000.0
                return AgentResponse(
                    request_id=request_id,
                    question=question,
                    sql="",
                    validation_status="UNSUPPORTED",
                    answer=self.formatter.format_unsupported(question, gen_response.explanation),
                    attempts=attempt,
                    total_time_ms=round(elapsed_ms, 2),
                )

            # Validate generated SQL with AST validator
            val_result = self.validator.validate(gen_response.sql, schema=schema)
            if val_result.is_valid:
                logger.info(f"[{request_id}] SQL validation PASSED.")
                break
            else:
                logger.warning(f"[{request_id}] SQL validation FAILED: {val_result.error_message}")
                error_feedback = f"SQL rejected by security/schema policy: {val_result.error_message}"

        # Check if validation succeeded after loop
        if not val_result or not val_result.is_valid:
            logger.error(f"[{request_id}] All generation attempts exhausted without passing validation.")
            elapsed_ms = (time.monotonic() - start_time) * 1000.0
            last_sql = gen_response.sql if gen_response else None
            last_err = val_result.error_message if val_result else "Failed to generate valid SQL."
            return AgentResponse(
                request_id=request_id,
                question=question,
                sql=last_sql,
                parameters=gen_response.parameters if gen_response else {},
                assumptions=gen_response.assumptions if gen_response else [],
                validation_status="REJECTED",
                answer=self.formatter.format_validation_error(question, last_err),
                attempts=attempt,
                total_time_ms=round(elapsed_ms, 2),
            )

        # 4. Safe Read-Only Execution
        validated_query = ValidatedQuery(
            sql=gen_response.sql,
            parameters=gen_response.parameters,
            validation_result=val_result,
        )

        exec_result = self.executor.execute(validated_query)

        # 5. Answer formatting
        if not exec_result.success:
            answer = self.formatter.format_execution_error(exec_result.error_message or "Unknown execution error")
        elif exec_result.is_empty:
            answer = self.formatter.format_empty_result(question, gen_response.assumptions)
        else:
            answer = self.formatter.format_success(
                question=question,
                result=exec_result,
                assumptions=gen_response.assumptions,
                explanation=gen_response.explanation,
            )

        elapsed_ms = (time.monotonic() - start_time) * 1000.0
        logger.info(f"[{request_id}] Query completed in {elapsed_ms:.1f}ms. Success: {exec_result.success}")

        return AgentResponse(
            request_id=request_id,
            question=question,
            sql=val_result.sanitized_sql or gen_response.sql,
            parameters=gen_response.parameters,
            assumptions=gen_response.assumptions,
            validation_status="PASSED",
            execution_result=exec_result,
            answer=answer,
            attempts=attempt,
            total_time_ms=round(elapsed_ms, 2),
        )
