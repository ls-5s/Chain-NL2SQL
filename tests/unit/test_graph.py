from pathlib import Path

from app.api.authorization import AccessPolicy
from app.db.sqlite_adapter import SQLiteAdapter
from app.graph.builder import SQLiteSchemaRetriever, build_query_graph
from app.graph.state import create_initial_state
from tests.fakes.fake_llm import FakeLLM


ROOT = Path(__file__).resolve().parents[2]


def test_minimal_graph_generates_validates_and_executes_sql() -> None:
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    policy = AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=frozenset({"users", "products", "orders", "order_items"}),
        allowed_columns={
            "users": frozenset({"id", "name", "email", "created_at"}),
            "products": frozenset({"id", "name", "category", "price"}),
            "orders": frozenset({"id", "user_id", "status", "total_amount", "created_at"}),
            "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
        },
    )
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=FakeLLM("SELECT COUNT(*) AS count FROM users"),
        schema_retriever=SQLiteSchemaRetriever(adapter),
        access_policy=policy,
        query_timeout_seconds=15,
    )

    state = graph.invoke(create_initial_state(
        request_id="test-request",
        question="查询用户数量",
        database_id="demo",
        dialect="sqlite",
        max_iterations=1,
    ))

    assert state["status"] == "succeeded"
    assert state["query_result"].rows == [[3]]
    assert state["final_answer"] == "查询完成，共返回 1 行结果。"
