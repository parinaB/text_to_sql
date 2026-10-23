"""Unit tests for embedding providers and ChromaDB retrieval."""

import math
import pytest
from embeddings import (
    DeterministicTestEmbeddingProvider,
    OllamaEmbeddingProvider,
    EmbeddingServiceUnavailableError,
    get_embedding_provider,
)
from retriever import (
    index_all_context,
    retrieve_context,
    get_chroma_client,
    RetrievedContext,
)


def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def test_deterministic_embedding_provider():
    """Verify deterministic provider produces normalized vectors with semantic clustering."""
    provider = DeterministicTestEmbeddingProvider(dimension=128)
    assert provider.dimension == 128
    assert provider.provider_name == "deterministic-test"

    v1 = provider.embed_text("orders placed in October 2026")
    v2 = provider.embed_text("October 2026 customer orders")
    v3 = provider.embed_text("airplane engine turbine maintenance schedule")

    # Vector length must be approximately 1.0 (normalized)
    assert pytest.approx(math.sqrt(sum(x * x for x in v1)), abs=1e-3) == 1.0

    # Semantic similarity: related phrases should have higher cosine similarity than unrelated phrases
    sim_related = cosine_similarity(v1, v2)
    sim_unrelated = cosine_similarity(v1, v3)

    assert sim_related > sim_unrelated
    assert sim_related > 0.5


def test_ollama_provider_unreachable_error():
    """Verify Ollama provider raises EmbeddingServiceUnavailableError when server is offline."""
    # Point to invalid host/port
    provider = OllamaEmbeddingProvider(base_url="http://127.0.0.1:54321", model_name="nomic-embed-text")
    with pytest.raises(EmbeddingServiceUnavailableError) as exc_info:
        provider.embed_text("Test query")

    assert "Could not connect to Ollama" in str(exc_info.value)
    assert "ollama.com" in str(exc_info.value)


def test_chromadb_indexing_and_idempotency(temp_chroma_dir):
    """Verify ChromaDB indexing populates collections without duplicating on re-index."""
    provider = DeterministicTestEmbeddingProvider(dimension=256)

    # First index
    stats1 = index_all_context(chroma_dir=temp_chroma_dir, provider=provider)
    assert stats1["schema_count"] == 4
    assert stats1["few_shot_count"] == 7

    # Second index (must not duplicate records)
    stats2 = index_all_context(chroma_dir=temp_chroma_dir, provider=provider)
    assert stats2["schema_count"] == 4
    assert stats2["few_shot_count"] == 7


def test_chromadb_retrieval(temp_chroma_dir):
    """Verify retrieving context for a query returns relevant schema and few-shot examples."""
    provider = DeterministicTestEmbeddingProvider(dimension=256)
    index_all_context(chroma_dir=temp_chroma_dir, provider=provider)

    ctx = retrieve_context(
        question="How many orders did we receive in October 2026?",
        chroma_dir=temp_chroma_dir,
        top_k_schema=2,
        top_k_examples=2,
        provider=provider,
    )

    assert isinstance(ctx, RetrievedContext)
    assert len(ctx.schema_snippets) > 0
    assert len(ctx.few_shot_examples) > 0

    # Verify orders table was retrieved
    table_names = [s.table_name for s in ctx.schema_snippets]
    assert "orders" in table_names

    # Verify few shot example
    ex_questions = [ex.question for ex in ctx.few_shot_examples]
    assert any("October 2026" in q for q in ex_questions)

    # Test prompt formatting
    formatted = ctx.format_for_prompt()
    assert "### Relevant Schema Context:" in formatted
    assert "### Relevant Question-to-SQL Examples (Reference Only):" in formatted
    assert "Reference Only" in formatted


def test_empty_query_retrieval(temp_chroma_dir):
    """Verify whitespace or empty queries return empty context without crashing."""
    ctx = retrieve_context(question="   ", chroma_dir=temp_chroma_dir)
    assert len(ctx.schema_snippets) == 0
    assert len(ctx.few_shot_examples) == 0
