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
            table_name="用户",
            content="TABLE 用户\nCOLUMNS 编号 INTEGER, 邮箱 TEXT, 用户名称 TEXT\nPRIMARY KEY 编号\nFOREIGN KEYS none",
            database_id="demo",
            column_names=["编号", "邮箱", "用户名称"],
        ),
        SchemaDocument(
            table_name="订单",
            content="TABLE 订单\nCOLUMNS 编号 INTEGER, 用户编号 INTEGER, 实付金额 REAL\nPRIMARY KEY 编号\nFOREIGN KEYS 用户编号->用户.编号",
            database_id="demo",
            column_names=["编号", "用户编号", "实付金额"],
        ),
    ]


def retrieval_source(database_id: str) -> SchemaRetrieval:
    assert database_id == "demo"
    return SchemaRetrieval(documents=documents(), schema_version="v1")


def test_bm25_roundtrip(tmp_path: Path) -> None:
    store = BM25Store.build(tmp_path, documents())
    loaded = BM25Store.load(tmp_path)
    assert [hit.document_id for hit in loaded.query("邮箱", 1)] == ["0"]
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
        question="订单",
    )
    assert [item.document.table_name for item in ranked] == ["订单", "用户"]


def test_index_manager_filters_columns_and_persists(tmp_path: Path) -> None:
    manager = SchemaIndexManager(retrieval_source, root=tmp_path, mode="bm25", top_k=5)
    request = SchemaRetrievalRequest(
        question="用户 邮箱",
        database_id="demo",
        dialect="sqlite",
        allowed_tables=frozenset({"用户"}),
        allowed_columns={"用户": frozenset({"编号", "用户名称"})},
    )
    result = manager.retrieve(request)
    assert [document.table_name for document in result.documents] == ["用户"]
    assert result.documents[0].column_names == ["编号", "用户名称"]
    assert "邮箱" not in result.documents[0].content
    manifests = list((tmp_path / "demo" / "v1").glob("*/manifest.json"))
    assert len(manifests) == 1
    manifest = manifests[0].read_text(encoding="utf-8")
    assert '"scope_hash"' in manifest
    assert '"tokenizer_version": "aliases-v2"' in manifest
    bm25_payload = manifests[0].with_name("bm25.json").read_text(encoding="utf-8")
    assert '"table_name": "用户"' in bm25_payload
    assert '"table_name": "订单"' not in bm25_payload

    second = manager.retrieve(request)
    assert second.schema_version == "v1"
    assert second.documents[0].column_names == ["编号", "用户名称"]


def test_index_manager_empty_table_allowlist_returns_no_documents(tmp_path: Path) -> None:
    manager = SchemaIndexManager(retrieval_source, root=tmp_path, mode="bm25", top_k=5)

    result = manager.retrieve(
        SchemaRetrievalRequest(
            question="查询用户数量",
            database_id="demo",
            dialect="sqlite",
            allowed_tables=frozenset(),
            allowed_columns={},
        )
    )

    assert result.documents == []


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
        SchemaRetrievalRequest("用户 邮箱", "demo", "sqlite", frozenset({"用户"}), {"用户": frozenset({"编号", "邮箱", "用户名称"})})
    )
    assert result.retrieval_mode == "bm25"
    assert result.documents[0].table_name == "用户"


def test_bm25_aliases_retrieve_user_for_chinese_question(tmp_path: Path) -> None:
    manager = SchemaIndexManager(retrieval_source, root=tmp_path, mode="bm25", top_k=2)
    result = manager.retrieve(
        SchemaRetrievalRequest(
            question="查询用户数量",
            database_id="demo",
            dialect="sqlite",
            allowed_tables=frozenset({"用户", "订单"}),
            allowed_columns={},
        )
    )
    assert result.documents
    assert "用户" in {document.table_name for document in result.documents}


def test_bm25_miss_falls_back_to_all_authorized_schema(tmp_path: Path) -> None:
    articles = SchemaDocument(
        table_name="文章",
        content="TABLE 文章\nCOLUMNS 编号 BIGINT, 标题 VARCHAR\nPRIMARY KEY 编号\nFOREIGN KEYS none",
        database_id="test",
        column_names=["编号", "标题"],
        dialect="mysql",
    )
    users = SchemaDocument(
        table_name="用户",
        content="TABLE 用户\nCOLUMNS 编号 BIGINT, 用户名称 VARCHAR\nPRIMARY KEY 编号\nFOREIGN KEYS none",
        database_id="test",
        column_names=["编号", "用户名称"],
        dialect="mysql",
    )

    def source(database_id: str) -> SchemaRetrieval:
        assert database_id == "test"
        return SchemaRetrieval(documents=[articles, users], schema_version="test-v1")

    manager = SchemaIndexManager(source, root=tmp_path, mode="bm25", top_k=1)
    result = manager.retrieve(
        SchemaRetrievalRequest(
            question="查询南极气候",
            database_id="test",
            dialect="mysql",
            allowed_tables=frozenset({"文章", "用户"}),
            allowed_columns={},
        )
    )

    assert result.retrieval_mode == "authorized_full_schema"
    assert result.retrieval_scores == {}
    assert [document.table_name for document in result.documents] == ["文章", "用户"]


def test_bm25_miss_fallback_never_includes_unauthorized_schema(tmp_path: Path) -> None:
    authorized = documents()[0]
    unauthorized = documents()[1]

    def source(database_id: str) -> SchemaRetrieval:
        return SchemaRetrieval(documents=[authorized, unauthorized], schema_version="v1")

    manager = SchemaIndexManager(source, root=tmp_path, mode="bm25", top_k=5)
    result = manager.retrieve(
        SchemaRetrievalRequest(
            question="查询博客文章",
            database_id="demo",
            dialect="sqlite",
            allowed_tables=frozenset({"用户"}),
            allowed_columns={},
        )
    )

    assert result.retrieval_mode == "authorized_full_schema"
    assert [document.table_name for document in result.documents] == ["用户"]


def test_bm25_miss_continues_graph_with_authorized_schema(tmp_path: Path) -> None:
    class Executor:
        def inspect_schema(self, database_id: str) -> SchemaRetrieval:
            return retrieval_source(database_id)

        def get_schema_version(self, database_id: str) -> str:
            return "v1"

        def execute_readonly(self, *args, **kwargs) -> QueryResult:
            return QueryResult(columns=["count"], rows=[[2]], row_count=1)

    executor = Executor()
    llm = FakeLLM([
        '{"intent":"data_query","confidence":0.95,"reason":"查询本地文章数据"}',
        'SELECT COUNT(*) FROM "用户"',
    ])
    retriever = SchemaIndexManager(
        retrieval_source,
        root=tmp_path,
        mode="bm25",
        top_k=1,
    )
    graph = build_query_graph(
        database_executor=executor,
        llm_client=llm,
        schema_retriever=retriever,
        access_policy=AccessPolicy(
            allowed_database_ids=frozenset({"demo"}),
            allowed_tables=frozenset({"用户", "订单"}),
            allowed_columns={},
        ),
        query_timeout_seconds=5,
    )

    state = graph.invoke(
        create_initial_state(
            request_id="bm25-miss-graph",
            question="查询有哪些博客文章",
            database_id="demo",
            dialect="sqlite",
            max_iterations=1,
        )
    )

    assert state["status"] == "succeeded"
    assert state["retrieval_mode"] == "authorized_full_schema"
    assert state["retrieved_tables"] == ["用户", "订单"]
    assert state["query_result"].rows == [[2]]
    assert llm.prompts


def test_schema_source_permission_error_is_controlled(tmp_path: Path) -> None:
    def denied_source(database_id: str) -> SchemaRetrieval:
        raise PermissionError("manifest denied")

    manager = SchemaIndexManager(denied_source, root=tmp_path, mode="bm25")
    request = SchemaRetrievalRequest("用户", "demo", "sqlite", frozenset({"用户"}), {})
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
            allowed_tables=frozenset({"用户"}),
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


def test_sqlite_schema_retriever_empty_table_allowlist_returns_no_documents() -> None:
    class SchemaOnlyExecutor:
        def inspect_schema(self, database_id: str) -> SchemaRetrieval:
            return retrieval_source(database_id)

    result = SQLiteSchemaRetriever(SchemaOnlyExecutor()).retrieve(
        SchemaRetrievalRequest(
            question="查询用户数量",
            database_id="demo",
            dialect="sqlite",
            allowed_tables=frozenset(),
            allowed_columns={},
        )
    )

    assert result.documents == []


def test_schema_index_manager_reaches_sql_prompt_for_chinese_query(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    adapter = SQLiteAdapter("demo", str(root / "data" / "demo.sqlite"))
    llm = FakeLLM(['SELECT COUNT(*) AS "用户数量" FROM "用户"'])
    retriever = SchemaIndexManager(adapter.inspect_schema, root=tmp_path, mode="bm25", top_k=2)
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=llm,
        schema_retriever=retriever,
        access_policy=AccessPolicy(
            allowed_database_ids=frozenset({"demo"}),
            allowed_tables=frozenset({"用户", "订单", "商品", "订单明细"}),
            allowed_columns={},
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
    assert "用户" in state["retrieved_tables"]
    assert any("TABLE 用户" in prompt.to_string() for prompt in llm.prompts)
    assert state["query_result"].rows == [[1000]]


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
    llm = FakeLLM(['SELECT COUNT(*) FROM "用户"', 'SELECT COUNT(*) FROM "用户"'])
    graph = build_query_graph(
        database_executor=executor,
        llm_client=llm,
        schema_retriever=SQLiteSchemaRetriever(executor),
        access_policy=AccessPolicy(
            allowed_database_ids=frozenset({"demo"}),
            allowed_tables=frozenset({"用户"}),
            allowed_columns={"用户": frozenset({"编号", "邮箱", "用户名称"})},
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
    assert len(llm.prompts) == 3
    assert "TABLE 用户" in llm.prompts[1].to_string()


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
        SchemaRetrievalRequest("邮箱", "demo", "sqlite", frozenset({"用户", "订单"}), {})
    )
    assert result.retrieval_mode == "bm25"
    assert result.documents[0].table_name == "用户"


def test_vector_index_with_injected_embedding(tmp_path: Path) -> None:
    class FakeEmbedding:
        model_name = "fake-embedding"

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0] if "邮箱" in text else [0.0, 1.0] for text in texts]

        def embed_query(self, text: str) -> list[float]:
            return [1.0, 0.0] if "邮箱" in text else [0.0, 1.0]

    class FakeReranker:
        model_name = "fake-reranker"

        def rerank(self, question: str, contents: list[str]) -> list[float]:
            return [1.0 if "邮箱" in content else 0.0 for content in contents]

    manager = SchemaIndexManager(
        retrieval_source,
        root=tmp_path,
        mode="vector",
        fallback_mode="none",
        embedding_factory=FakeEmbedding,
        reranker_factory=FakeReranker,
    )
    result = manager.retrieve(
        SchemaRetrievalRequest("邮箱", "demo", "sqlite", frozenset({"用户", "订单"}), {})
    )
    assert result.retrieval_mode == "vector"
    assert result.documents[0].table_name == "用户"


class DriftExecutor:
    def get_schema_version(self, database_id: str) -> str:
        return "v2"

    def execute_readonly(self, *args, **kwargs) -> QueryResult:
        raise AssertionError("drift must block execution")


def test_execution_blocks_schema_drift() -> None:
    policy = AccessPolicy(allowed_database_ids=frozenset({"demo"}), allowed_tables=frozenset({"用户"}))
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
