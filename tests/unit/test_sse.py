import asyncio
import json
from pathlib import Path

from app.api.authorization import AccessPolicy
from app.api.routes import _stream_graph
from app.db.sqlite_adapter import SQLiteAdapter
from app.graph.builder import SQLiteSchemaRetriever, build_query_graph
from app.graph.state import create_initial_state
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


def state(question: str):
    return create_initial_state(
        request_id="sse-test",
        question=question,
        database_id="demo",
        dialect="sqlite",
        max_iterations=1,
    )


def events(chunks: list[str]) -> list[tuple[str, dict[str, object]]]:
    result = []
    for chunk in chunks:
        lines = chunk.strip().splitlines()
        result.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return result


def run_stream(graph, initial, database):
    return asyncio.run(_collect(graph, initial, database))


async def _collect(graph, initial, database):
    return [chunk async for chunk in _stream_graph(graph, initial, database)]


def test_sse_data_path_emits_expected_events() -> None:
    database = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    graph = build_query_graph(
        database_executor=database,
        llm_client=FakeLLM(['{"intent":"data_query"}', "SELECT COUNT(*) AS count FROM users"]),
        schema_retriever=SQLiteSchemaRetriever(database),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    result = events(run_stream(graph, state("查询用户数量"), database))

    assert [name for name, _ in result] == ["start", "progress", "progress", "progress", "progress", "progress", "progress", "complete"]
    assert result[1][1]["node"] == "intent_gate"
    assert result[1][1]["intent"] == "data_query"
    assert result[-1][1]["intent"] == "data_query"


def test_sse_general_path_skips_database_nodes() -> None:
    database = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    graph = build_query_graph(
        database_executor=database,
        llm_client=FakeLLM(['{"intent":"general_chat"}', "你好，有什么可以帮你？"]),
        schema_retriever=SQLiteSchemaRetriever(database),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    result = events(run_stream(graph, state("你好"), database))
    nodes = [data.get("node") for name, data in result if name == "progress"]

    assert nodes == ["intent_gate", "general_answer", "finalize"]
    assert result[-1][1]["intent"] == "general_chat"


def test_sse_clarification_path_skips_database_nodes() -> None:
    database = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    graph = build_query_graph(
        database_executor=database,
        llm_client=FakeLLM(['{"intent":"clarification"}', "请补充时间范围。"]),
        schema_retriever=SQLiteSchemaRetriever(database),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    result = events(run_stream(graph, state("帮我看看数据"), database))
    nodes = [data.get("node") for name, data in result if name == "progress"]

    assert nodes == ["intent_gate", "clarify", "finalize"]
    assert result[-1][1]["intent"] == "clarification"


def test_sse_model_failure_emits_error_event() -> None:
    database = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    graph = build_query_graph(
        database_executor=database,
        llm_client=FakeLLM([RuntimeError("provider unavailable")]),
        schema_retriever=SQLiteSchemaRetriever(database),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    result = events(run_stream(graph, state("你好"), database))

    assert [name for name, _ in result] == ["start", "error"]
    assert result[-1][1]["status_code"] == 502
