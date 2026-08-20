from __future__ import annotations

from pathlib import Path

import pytest

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutor
from app.db.base import DatabaseExecutionError
from app.db.sqlite_adapter import SQLiteAdapter
from app.graph.execution_node import make_execution_node
from app.graph.builder import SQLiteSchemaRetriever, build_query_graph
from app.rag.bm25_store import BM25Hit, BM25Store
from app.rag.hybrid_retriever import reciprocal_rank_fusion
from app.rag.index_manager import SchemaIndexManager
from app.rag.retriever import SchemaRetrievalRequest
from app.rag.retriever import SchemaRetrievalError
from app.rag.vector_store import VectorHit
from app.schemas.domain import QueryResult, SchemaDocument, SchemaRetrieval
from app.graph.state import create_initial_state
from tests.fakes.fake_llm import FakeLLM


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
    manifests = list((tmp_path / "demo" / "v1").glob("*/manifest.json"))
    assert len(manifests) == 1
    manifest = manifests[0].read_text(encoding="utf-8")
    assert '"scope_hash"' in manifest
    assert '"tokenizer_version": "aliases-v1"' in manifest
    bm25_payload = manifests[0].with_name("bm25.json").read_text(encoding="utf-8")
    assert '"table_name": "users"' in bm25_payload
    assert '"table_name": "orders"' not in bm25_payload

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


def test_bm25_aliases_retrieve_users_for_chinese_question(tmp_path: Path) -> None:
    manager = SchemaIndexManager(retrieval_source, root=tmp_path, mode="bm25", top_k=2)
    result = manager.retrieve(
        SchemaRetrievalRequest(
            question="查询用户数量",
            database_id="demo",
            dialect="sqlite",
            allowed_tables=frozenset({"users", "orders"}),
            allowed_columns={},
        )
    )
    assert result.documents
    assert "users" in {document.table_name for document in result.documents}


def test_schema_source_permission_error_is_controlled(tmp_path: Path) -> None:
    def denied_source(database_id: str) -> SchemaRetrieval:
        raise PermissionError("manifest denied")

    manager = SchemaIndexManager(denied_source, root=tmp_path, mode="bm25")
    request = SchemaRetrievalRequest("users", "demo", "sqlite", frozenset({"users"}), {})
    with pytest.raises(SchemaRetrievalError, match="Unable to read"):
        manager.retrieve(request)


class EmptyRetriever:
    def retrieve(self, request: SchemaRetrievalRequest) -> SchemaRetrieval:
        return SchemaRetrieval(documents=[], schema_version="v1", retrieval_mode="bm25")


class NoExecute:
    def execute_readonly(self, *args, **kwargs):
        raise AssertionError("empty retrieval must not execute SQL")

    def get_schema_version(self, database_id: str) -> str:
        return "v1"


def test_empty_retrieval_fails_closed_before_sql_generation() -> None:
    llm = FakeLLM(["SELECT 0"])
    graph = build_query_graph(
        database_executor=NoExecute(),
        llm_client=llm,
        schema_retriever=EmptyRetriever(),
        access_policy=AccessPolicy(
            allowed_database_ids=frozenset({"demo"}),
            allowed_tables=frozenset({"users"}),
        ),
        query_timeout_seconds=5,
    )
    state = graph.invoke(
        create_initial_state(
            request_id="empty",
            question="查询用户数量",
            database_id="demo",
            dialect="sqlite",
            max_iterations=1,
        )
    )
    assert state["status"] == "failed"
    assert state["error_category"] == "schema_retrieval_error"
    assert "generated_sql" not in state
    assert not llm.prompts


def test_schema_index_manager_reaches_sql_prompt_for_chinese_query(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    adapter = SQLiteAdapter("demo", str(root / "data" / "demo.sqlite"))
    llm = FakeLLM(["SELECT COUNT(*) AS user_count FROM users"])
    retriever = SchemaIndexManager(adapter.inspect_schema, root=tmp_path, mode="bm25", top_k=2)
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=llm,
        schema_retriever=retriever,
        access_policy=AccessPolicy(
            allowed_database_ids=frozenset({"demo"}),
            allowed_tables=frozenset({"users", "orders", "products", "order_items"}),
            allowed_columns={
                "users": frozenset({"id", "name", "email", "created_at"}),
                "orders": frozenset({"id", "user_id", "status", "total_amount", "created_at"}),
                "products": frozenset({"id", "name", "category", "price"}),
                "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
            },
        ),
        query_timeout_seconds=5,
    )
    state = graph.invoke(
        create_initial_state(
            request_id="rag-e2e",
            question="查询用户数量",
            database_id="demo",
            dialect="sqlite",
            max_iterations=1,
        )
    )
    assert state["status"] == "succeeded"
    assert "users" in state["retrieved_tables"]
    assert "TABLE users" in llm.prompts[1 if len(llm.prompts) > 1 else 0].to_string()
    assert state["query_result"].rows == [[3]]


class RepairExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def inspect_schema(self, database_id: str) -> SchemaRetrieval:
        return retrieval_source(database_id)

    def get_schema_version(self, database_id: str) -> str:
        return "v1"

    def execute_readonly(self, *args, **kwargs) -> QueryResult:
        self.calls += 1
        if self.calls == 1:
            raise DatabaseExecutionError("syntax_error", "The read-only query could not be executed.")
        return QueryResult(columns=["count"], rows=[[2]], row_count=1)

    def close(self) -> None:
        return None


def test_repair_reuses_fixed_schema_and_retries_execution() -> None:
    executor = RepairExecutor()
    llm = FakeLLM(["SELECT COUNT(*) FROM users", "SELECT COUNT(*) FROM users"])
    graph = build_query_graph(
        database_executor=executor,
        llm_client=llm,
        schema_retriever=SQLiteSchemaRetriever(executor),
        access_policy=AccessPolicy(
            allowed_database_ids=frozenset({"demo"}),
            allowed_tables=frozenset({"users"}),
            allowed_columns={"users": frozenset({"id", "email", "name"})},
        ),
        query_timeout_seconds=5,
    )
    state = graph.invoke(
        create_initial_state(
            request_id="repair",
            question="查询用户数量",
            database_id="demo",
            dialect="sqlite",
            max_iterations=2,
        )
    )
    assert state["status"] == "succeeded"
    assert state["query_result"].rows == [[2]]
    assert state["iteration"] == 2
    assert len(llm.prompts) == 2
    assert "TABLE users" in llm.prompts[1].to_string()


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
