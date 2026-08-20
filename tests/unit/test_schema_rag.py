from __future__ import annotations

from pathlib import Path

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutor
from app.graph.execution_node import make_execution_node
from app.rag.bm25_store import BM25Hit, BM25Store
from app.rag.hybrid_retriever import reciprocal_rank_fusion
from app.rag.index_manager import SchemaIndexManager
from app.rag.retriever import SchemaRetrievalRequest
from app.rag.vector_store import VectorHit
from app.schemas.domain import QueryResult, SchemaDocument, SchemaRetrieval


def documents() -> list[SchemaDocument]:
    return [
        SchemaDocument(
            table_name="users",
            content="TABLE users\nCOLUMNS id INTEGER, email TEXT, name TEXT\nPRIMARY KEY id\nFOREIGN KEYS none",
            database_id="demo",
            column_names=["id", "email", "name"],
        ),
        SchemaDocument(
            table_name="orders",
            content="TABLE orders\nCOLUMNS id INTEGER, user_id INTEGER, total_amount REAL\nPRIMARY KEY id\nFOREIGN KEYS user_id->users.id",
            database_id="demo",
            column_names=["id", "user_id", "total_amount"],
        ),
    ]


def retrieval_source(database_id: str) -> SchemaRetrieval:
    assert database_id == "demo"
    return SchemaRetrieval(documents=documents(), schema_version="v1")


def test_bm25_roundtrip(tmp_path: Path) -> None:
    store = BM25Store.build(tmp_path, documents())
    loaded = BM25Store.load(tmp_path)
    assert [hit.document_id for hit in loaded.query("email", 1)] == ["0"]
    assert len(store.documents) == 2


def test_rrf_deduplicates_and_applies_reranker() -> None:
    class FakeReranker:
        def rerank(self, question: str, contents: list[str]) -> list[float]:
            return [0.1, 0.9]

    ranked = reciprocal_rank_fusion(
        documents(),
        [BM25Hit("0", 4.0), BM25Hit("1", 3.0)],
        [VectorHit("0", 0.8)],
        top_k=2,
        reranker=FakeReranker(),
        question="orders",
    )
    assert [item.document.table_name for item in ranked] == ["orders", "users"]


def test_index_manager_filters_columns_and_persists(tmp_path: Path) -> None:
    manager = SchemaIndexManager(retrieval_source, root=tmp_path, mode="bm25", top_k=5)
    request = SchemaRetrievalRequest(
        question="users email",
        database_id="demo",
        dialect="sqlite",
        allowed_tables=frozenset({"users"}),
        allowed_columns={"users": frozenset({"id", "name"})},
    )
    result = manager.retrieve(request)
    assert [document.table_name for document in result.documents] == ["users"]
    assert result.documents[0].column_names == ["id", "name"]
    assert "email" not in result.documents[0].content
    assert (tmp_path / "demo" / "v1" / "manifest.json").exists()

    second = manager.retrieve(request)
    assert second.schema_version == "v1"
    assert second.documents[0].column_names == ["id", "name"]


def test_hybrid_degrades_to_bm25_when_embedding_unavailable(tmp_path: Path) -> None:
    def unavailable_embedding():
        raise RuntimeError("embedding unavailable")

    manager = SchemaIndexManager(
        retrieval_source,
        root=tmp_path,
        mode="hybrid",
        fallback_mode="bm25",
        embedding_factory=unavailable_embedding,
    )
    result = manager.retrieve(
        SchemaRetrievalRequest("users email", "demo", "sqlite", frozenset({"users"}), {"users": frozenset({"id", "email", "name"})})
    )
    assert result.retrieval_mode == "bm25"
    assert result.documents[0].table_name == "users"


def test_reranker_failure_recomputes_bm25(tmp_path: Path) -> None:
    def unavailable_reranker():
        raise RuntimeError("reranker unavailable")

    manager = SchemaIndexManager(
        retrieval_source,
        root=tmp_path,
        mode="hybrid",
        fallback_mode="bm25",
        reranker_factory=unavailable_reranker,
    )
    result = manager.retrieve(
        SchemaRetrievalRequest("email", "demo", "sqlite", frozenset({"users", "orders"}), {})
    )
    assert result.retrieval_mode == "bm25"
    assert result.documents[0].table_name == "users"


def test_vector_index_with_injected_embedding(tmp_path: Path) -> None:
    class FakeEmbedding:
        model_name = "fake-embedding"

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0] if "email" in text else [0.0, 1.0] for text in texts]

        def embed_query(self, text: str) -> list[float]:
            return [1.0, 0.0] if "email" in text else [0.0, 1.0]

    class FakeReranker:
        model_name = "fake-reranker"

        def rerank(self, question: str, contents: list[str]) -> list[float]:
            return [1.0 if "email" in content else 0.0 for content in contents]

    manager = SchemaIndexManager(
        retrieval_source,
        root=tmp_path,
        mode="vector",
        fallback_mode="none",
        embedding_factory=FakeEmbedding,
        reranker_factory=FakeReranker,
    )
    result = manager.retrieve(
        SchemaRetrievalRequest("email", "demo", "sqlite", frozenset({"users", "orders"}), {})
    )
    assert result.retrieval_mode == "vector"
    assert result.documents[0].table_name == "users"


class DriftExecutor:
    def get_schema_version(self, database_id: str) -> str:
        return "v2"

    def execute_readonly(self, *args, **kwargs) -> QueryResult:
        raise AssertionError("drift must block execution")


def test_execution_blocks_schema_drift() -> None:
    policy = AccessPolicy(allowed_database_ids=frozenset({"demo"}), allowed_tables=frozenset({"users"}))
    node = make_execution_node(DriftExecutor(), policy, 5)
    state = {
        "request_id": "r",
        "question": "q",
        "database_id": "demo",
        "dialect": "sqlite",
        "iteration": 1,
        "max_iterations": 1,
        "trace": [],
        "status": "running",
        "schema_version": "v1",
        "validated_sql": "SELECT 1",
    }
    result = node(state)  # type: ignore[arg-type]
    assert result["error_category"] == "schema_changed"
