"""ChromaDB indexing and semantic retrieval for schema context and few-shot exemplars."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from pydantic import BaseModel, Field

from config import AppConfig, get_config
from embeddings import BaseEmbeddingProvider, get_embedding_provider


class SchemaSnippet(BaseModel):
    """Retrieved schema description snippet."""
    table_name: str
    description: str
    distance: float = 0.0


class FewShotExample(BaseModel):
    """Retrieved question-to-SQL exemplar."""
    id: str
    question: str
    sql: str
    explanation: str
    distance: float = 0.0


class RetrievedContext(BaseModel):
    """Aggregate semantic context retrieved for a user query."""
    question: str
    schema_snippets: List[SchemaSnippet] = Field(default_factory=list)
    few_shot_examples: List[FewShotExample] = Field(default_factory=list)

    def format_for_prompt(self) -> str:
        """Format retrieved context for injection into LLM system prompt."""
        parts = []

        if self.schema_snippets:
            parts.append("### Relevant Schema Context:")
            for s in self.schema_snippets:
                parts.append(f"- **Table `{s.table_name}`**: {s.description}")
            parts.append("")

        if self.few_shot_examples:
            parts.append("### Relevant Question-to-SQL Examples (Reference Only):")
            for ex in self.few_shot_examples:
                parts.append(f"Question: \"{ex.question}\"")
                parts.append(f"SQL:\n```sql\n{ex.sql}\n```")
                parts.append(f"Explanation: {ex.explanation}\n")

        return "\n".join(parts)


class ChromaEmbeddingAdapter(EmbeddingFunction):
    """Adapter allowing BaseEmbeddingProvider to be used natively by ChromaDB."""

    def __init__(self, provider: BaseEmbeddingProvider):
        self.provider = provider

    def name(self) -> str:
        return self.provider.provider_name

    def get_config(self) -> Dict[str, Any]:
        return {"provider": self.provider.provider_name}

    def __call__(self, input: Documents) -> Embeddings:
        return self.provider.embed_documents(list(input))


SCHEMA_DOCUMENTS = [
    {
        "id": "schema_customers",
        "table_name": "customers",
        "text": "The customers table stores customer profile information, including first_name, last_name, email, city, country, registration date (created_at), and customer account status (active, inactive, churned).",
    },
    {
        "id": "schema_products",
        "table_name": "products",
        "text": "The products table contains product catalog details: product_id, product_name, category (Electronics, Furniture, Accessories, Office Supplies), unit_price, cost, stock_quantity, and active status (is_active).",
    },
    {
        "id": "schema_orders",
        "table_name": "orders",
        "text": "The orders table tracks sales transactions: order_id, customer_id (foreign key to customers), order_date (YYYY-MM-DD), order_status (completed, pending, cancelled, shipped), total_amount in USD, and shipping_city.",
    },
    {
        "id": "schema_order_items",
        "table_name": "order_items",
        "text": "The order_items table holds line-item details for each order: item_id, order_id (foreign key to orders), product_id (foreign key to products), purchased quantity, unit_price at sale, and discount applied.",
    },
]

FEW_SHOT_EXEMPLARS = [
    {
        "id": "few_shot_orders_month",
        "question": "How many orders did we receive in October 2026?",
        "sql": "SELECT COUNT(*) AS total_orders FROM orders WHERE order_date >= '2026-10-01' AND order_date <= '2026-10-31';",
        "explanation": "Counts total rows in orders table matching the October 2026 date window.",
    },
    {
        "id": "few_shot_revenue_month",
        "question": "What was our total revenue in September 2026?",
        "sql": "SELECT SUM(total_amount) AS total_revenue FROM orders WHERE order_date >= '2026-09-01' AND order_date <= '2026-09-30' AND order_status = 'completed';",
        "explanation": "Calculates sum of total_amount for all completed orders in September 2026.",
    },
    {
        "id": "few_shot_top_products",
        "question": "Which 5 products generated the most revenue?",
        "sql": "SELECT p.product_name, SUM(oi.quantity * (oi.unit_price - oi.discount)) AS total_revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_id, p.product_name ORDER BY total_revenue DESC LIMIT 5;",
        "explanation": "Joins order_items with products and aggregates gross revenue grouped by product name.",
    },
    {
        "id": "few_shot_avg_order_value",
        "question": "What is the average order value?",
        "sql": "SELECT AVG(total_amount) AS average_order_value FROM orders WHERE order_status = 'completed';",
        "explanation": "Computes average total_amount across completed orders.",
    },
    {
        "id": "few_shot_orders_per_customer",
        "question": "How many orders did each customer place?",
        "sql": "SELECT c.customer_id, c.first_name, c.last_name, COUNT(o.order_id) AS total_orders FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.first_name, c.last_name ORDER BY total_orders DESC;",
        "explanation": "Uses a LEFT JOIN to count orders per customer, preserving customers who have placed zero orders.",
    },
    {
        "id": "few_shot_unorderd_products",
        "question": "Which products have never been ordered?",
        "sql": "SELECT p.product_id, p.product_name FROM products p LEFT JOIN order_items oi ON p.product_id = oi.product_id WHERE oi.product_id IS NULL;",
        "explanation": "Identifies products with no corresponding entries in order_items.",
    },
    {
        "id": "few_shot_customers_zero_orders",
        "question": "Which customers have never placed an order?",
        "sql": "SELECT c.customer_id, c.first_name, c.last_name FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_id IS NULL;",
        "explanation": "Finds registered customers with zero associated records in orders.",
    },
]


def get_chroma_client(chroma_dir: Optional[str] = None) -> chromadb.ClientAPI:
    """Instantiate a persistent ChromaDB client."""
    cfg = get_config()
    target_dir = chroma_dir or cfg.chroma_persist_dir
    path_obj = Path(target_dir).resolve()
    path_obj.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path_obj))


def index_all_context(
    chroma_dir: Optional[str] = None,
    provider: Optional[BaseEmbeddingProvider] = None,
) -> Dict[str, int]:
    """Index schema descriptions and few-shot exemplars idempotently into ChromaDB."""
    client = get_chroma_client(chroma_dir)
    emb_provider = provider or get_embedding_provider()
    adapter = ChromaEmbeddingAdapter(emb_provider)

    # 1. Index Schema Context
    schema_col = client.get_or_create_collection(
        name="schema_context",
        embedding_function=adapter,
        metadata={"hnsw:space": "cosine"},
    )
    schema_ids = [doc["id"] for doc in SCHEMA_DOCUMENTS]
    schema_texts = [doc["text"] for doc in SCHEMA_DOCUMENTS]
    schema_metas = [{"table_name": doc["table_name"]} for doc in SCHEMA_DOCUMENTS]
    schema_col.upsert(ids=schema_ids, documents=schema_texts, metadatas=schema_metas)

    # 2. Index Few-Shot Exemplars
    few_shot_col = client.get_or_create_collection(
        name="few_shot_examples",
        embedding_function=adapter,
        metadata={"hnsw:space": "cosine"},
    )
    ex_ids = [ex["id"] for ex in FEW_SHOT_EXEMPLARS]
    ex_texts = [ex["question"] for ex in FEW_SHOT_EXEMPLARS]
    ex_metas = [{"sql": ex["sql"], "explanation": ex["explanation"]} for ex in FEW_SHOT_EXEMPLARS]
    few_shot_col.upsert(ids=ex_ids, documents=ex_texts, metadatas=ex_metas)

    return {
        "schema_count": schema_col.count(),
        "few_shot_count": few_shot_col.count(),
    }


def retrieve_context(
    question: str,
    chroma_dir: Optional[str] = None,
    top_k_schema: int = 2,
    top_k_examples: int = 3,
    provider: Optional[BaseEmbeddingProvider] = None,
) -> RetrievedContext:
    """Retrieve relevant schema descriptions and question-to-SQL exemplars for a query."""
    clean_question = question.strip()
    if not clean_question:
        return RetrievedContext(question=question)

    client = get_chroma_client(chroma_dir)
    emb_provider = provider or get_embedding_provider()
    adapter = ChromaEmbeddingAdapter(emb_provider)

    schema_snippets: List[SchemaSnippet] = []
    few_shot_examples: List[FewShotExample] = []

    # Query schema collection
    try:
        schema_col = client.get_collection(name="schema_context", embedding_function=adapter)
        schema_results = schema_col.query(query_texts=[clean_question], n_results=min(top_k_schema, schema_col.count()))
        if schema_results and schema_results["documents"] and schema_results["documents"][0]:
            docs = schema_results["documents"][0]
            metas = schema_results["metadatas"][0] if schema_results["metadatas"] else [{}] * len(docs)
            distances = schema_results["distances"][0] if schema_results.get("distances") else [0.0] * len(docs)
            for doc, meta, dist in zip(docs, metas, distances):
                schema_snippets.append(
                    SchemaSnippet(
                        table_name=meta.get("table_name", "unknown"),
                        description=doc,
                        distance=float(dist) if dist is not None else 0.0,
                    )
                )
    except Exception:
        # Collection might not be indexed yet
        pass

    # Query few-shot collection
    try:
        few_shot_col = client.get_collection(name="few_shot_examples", embedding_function=adapter)
        fs_results = few_shot_col.query(query_texts=[clean_question], n_results=min(top_k_examples, few_shot_col.count()))
        if fs_results and fs_results["documents"] and fs_results["documents"][0]:
            q_texts = fs_results["documents"][0]
            ids = fs_results["ids"][0] if fs_results["ids"] else [""] * len(q_texts)
            metas = fs_results["metadatas"][0] if fs_results["metadatas"] else [{}] * len(q_texts)
            distances = fs_results["distances"][0] if fs_results.get("distances") else [0.0] * len(q_texts)
            for q_text, ex_id, meta, dist in zip(q_texts, ids, metas, distances):
                few_shot_examples.append(
                    FewShotExample(
                        id=ex_id,
                        question=q_text,
                        sql=meta.get("sql", ""),
                        explanation=meta.get("explanation", ""),
                        distance=float(dist) if dist is not None else 0.0,
                    )
                )
    except Exception:
        pass

    return RetrievedContext(
        question=clean_question,
        schema_snippets=schema_snippets,
        few_shot_examples=few_shot_examples,
    )
