import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.api.authorization import AccessPolicy
from app.api.routes import _stream_graph
from app.db.sqlite_adapter import SQLiteAdapter
from app.graph.builder import SQLiteSchemaRetriever, build_query_graph
from app.graph.state import create_initial_state
from app.schemas.domain import QueryIntent, QueryStatus
from tests.fakes.fake_llm import FakeLLM


ROOT = Path(__file__).resolve().parents[2]


def policy() -> AccessPolicy:
    return AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=frozenset({"users", "products", "orders", "order_items"}),
        allowed_columns={
            "users": frozenset({"id", "name", "email", "created_at"}),
            "products": frozenset({"id", "name", "category", "price"}),
            "orders": frozenset({"id", "user_id", "status", "total_amount", "created_at"}),
            "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
        },
    )


def make_graph(adapter, llm):
    return build_query_graph(
        database_executor=adapter,
        llm_client=llm,
        schema_retriever=SQLiteSchemaRetriever(adapter),
        access_policy=policy(),
        query_timeout_seconds=15,
        result_summary_enabled=False,
    )


def test_general_answer_without_database_runtime_or_schema() -> None:
    class NoDatabase:
        def inspect_schema(self, *_):
            raise AssertionError("schema access")

        def execute_readonly(self, *_args, **_kwargs):
            raise AssertionError("sql access")

        def close(self):
            pass

    state = create_initial_state(request_id="general", question="你好", max_iterations=1)
    result = make_graph(NoDatabase(), FakeLLM(["你好。"])).invoke(state)
    assert result["intent"] == QueryIntent.GENERAL_CHAT
    assert result["status"] == QueryStatus.SUCCEEDED
    assert result["answer_source"] == "general_llm"
    assert "generated_sql" not in result


def test_ambiguous_question_persists_required_clarification() -> None:
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    result = make_graph(adapter, FakeLLM([])).invoke(
        create_initial_state(request_id="clarify", question="帮我看看数据", max_iterations=1)
    )
    assert result["intent"] == QueryIntent.CLARIFY
    assert result["status"] == QueryStatus.NEEDS_CLARIFICATION
    assert result["required_actions"] == ["provide_fields"]
    assert "pending_clarification" in result


def test_data_flow_is_the_only_path_that_reads_database() -> None:
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    result = make_graph(adapter, FakeLLM(["SELECT COUNT(*) AS count FROM users"])).invoke(
        create_initial_state(request_id="data", question="查询用户数量", database_id="demo", dialect="sqlite", max_iterations=1)
    )
    assert result["intent"] == QueryIntent.DATA_QUERY
    assert result["status"] == QueryStatus.SUCCEEDED
    assert result["query_result"].rows == [[3]]
    assert [event.node for event in result["trace"] if event.node == "result_guard"] == ["result_guard"]


def test_missing_database_requires_selection_without_sql() -> None:
    class NoDatabase:
        def inspect_schema(self, *_):
            raise AssertionError("schema access")

        def execute_readonly(self, *_args, **_kwargs):
            raise AssertionError("sql access")

        def close(self):
            pass

    result = make_graph(NoDatabase(), FakeLLM([])).invoke(
        create_initial_state(request_id="missing-db", question="查询用户数量", max_iterations=1)
    )
    assert result["status"] == QueryStatus.NEEDS_CLARIFICATION
    assert result["required_actions"] == ["select_database"]


def test_internal_knowledge_without_grounded_store_refuses_without_llm() -> None:
    class NoDatabase:
        def close(self):
            pass

    result = make_graph(NoDatabase(), FakeLLM([])).invoke(
        create_initial_state(request_id="knowledge", question="公司制度是什么", max_iterations=1)
    )
    assert result["status"] == QueryStatus.NO_GROUNDED_ANSWER
    assert result["final_answer"].startswith("NO_GROUNDED_ANSWER")


def test_sse_has_one_start_one_terminal_and_request_identity() -> None:
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    graph = make_graph(adapter, FakeLLM(["你好。"]))
    state = create_initial_state(request_id="sse-v1", question="你好", max_iterations=1)

    async def collect():
        return [item async for item in _stream_graph(graph, state, adapter)]

    chunks = asyncio.run(collect())
    events = []
    for chunk in chunks:
        lines = chunk.strip().splitlines()
        events.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    assert [name for name, _ in events].count("start") == 1
    assert [name for name, _ in events].count("complete") == 1
    assert events[-1][0] == "complete"
    assert all(data["request_id"] == "sse-v1" for _, data in events)


def test_conversation_idempotency_and_single_database_bind(tmp_path) -> None:
    from app.conversations.repository import ConversationRepository

    repository = ConversationRepository(tmp_path / "conversation.sqlite3")
    conversation = repository.create_conversation("user", None)
    first = repository.start_turn("user", conversation["id"], "查询用户", "", client_request_id="same")
    second = repository.start_turn("user", conversation["id"], "查询用户", "", client_request_id="same")
    assert first["turn_id"] == second["turn_id"]

    def bind(database_id):
        return repository.bind_database("user", conversation["id"], database_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(bind, ["demo", "other"]))
    assert sum(outcomes) == 1


def test_conversation_database_bind_api_rejects_second_binding(monkeypatch, tmp_path) -> None:
    from fastapi.testclient import TestClient

    from app.api import auth, routes
    from app.config.settings import get_settings
    from app.main import create_app

    monkeypatch.setenv("CONVERSATION_DATABASE_PATH", str(tmp_path / "conversation.sqlite3"))
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "123456")
    get_settings.cache_clear()
    auth._repositories.clear()
    routes._conversation_repositories.clear()
    client = TestClient(create_app())
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    conversation = client.post("/api/v1/conversations", json={"database_id": None}).json()

    assert client.post(f"/api/v1/conversations/{conversation['id']}/database", json={"database_id": "demo"}).status_code == 200
    assert client.post(f"/api/v1/conversations/{conversation['id']}/database", json={"database_id": "demo"}).status_code == 409
