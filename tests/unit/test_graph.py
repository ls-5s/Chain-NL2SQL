from pathlib import Path

import pytest

from app.api.authorization import AccessPolicy
from app.db.sqlite_adapter import SQLiteAdapter
from app.graph.builder import SQLiteSchemaRetriever, build_query_graph
from app.graph.state import create_initial_state
from app.schemas.domain import QueryIntent
from tests.fakes.fake_llm import FakeLLM


ROOT = Path(__file__).resolve().parents[2]


class UnexpectedDatabaseAccess:
    def inspect_schema(self, database_id: str):
        raise AssertionError("Non-data intent must not inspect Schema.")

    def execute_readonly(self, *args, **kwargs):
        raise AssertionError("Non-data intent must not execute SQL.")

    def close(self) -> None:
        return None


class UnexpectedRetriever:
    def retrieve(self, question: str, database_id: str):
        raise AssertionError("Non-data intent must not retrieve Schema.")


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


def initial_state(question: str):
    return create_initial_state(
        request_id="test-request",
        question=question,
        database_id="demo",
        dialect="sqlite",
        max_iterations=1,
    )


def test_data_intent_retrieves_schema_generates_and_executes_sql() -> None:
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    llm = FakeLLM([
        "SELECT COUNT(*) AS count FROM users",
    ])
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=llm,
        schema_retriever=SQLiteSchemaRetriever(adapter),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state("查询用户数量"))

    assert state["intent"] == QueryIntent.DATA_QUERY
    assert state["status"] == "succeeded"
    assert state["query_result"].rows == [[3]]
    assert state["final_answer"] == "查询完成，共返回 1 行结果。"
    assert len(llm.prompts) == 1
    assert state["intent_source"] == "rule"


@pytest.mark.parametrize("question", ["你好", "今天天气怎么样", "帮我写一封邮件"])
def test_general_chat_uses_llm_without_schema_or_sql_access(question: str) -> None:
    llm = FakeLLM(["你好，有什么可以帮你？"])
    graph = build_query_graph(
        database_executor=UnexpectedDatabaseAccess(),
        llm_client=llm,
        schema_retriever=UnexpectedRetriever(),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state(question))

    assert state["intent"] == QueryIntent.GENERAL_CHAT
    assert state["status"] == "succeeded"
    assert state["final_answer"] == "你好，有什么可以帮你？"
    assert "generated_sql" not in state
    assert len(llm.prompts) == 1
    assert state["intent_source"] == "rule"


def test_ambiguous_question_uses_llm_clarification_without_database_access() -> None:
    llm = FakeLLM(["请说明要查看的指标、时间范围和筛选条件。"])
    graph = build_query_graph(
        database_executor=UnexpectedDatabaseAccess(),
        llm_client=llm,
        schema_retriever=UnexpectedRetriever(),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state("帮我看看数据"))

    assert state["intent"] == QueryIntent.CLARIFICATION
    assert state["final_answer"] == "请说明要查看的指标、时间范围和筛选条件。"
    assert len(llm.prompts) == 1
    assert state["intent_source"] == "rule"


def test_invalid_intent_json_conservatively_uses_clarification() -> None:
    llm = FakeLLM(["这看起来像数据问题", "请说明需要查询的业务对象和时间范围。"])
    graph = build_query_graph(
        database_executor=UnexpectedDatabaseAccess(),
        llm_client=llm,
        schema_retriever=UnexpectedRetriever(),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state("这个事情怎么处理"))

    assert state["intent"] == QueryIntent.CLARIFICATION
    assert state["intent_classification_valid"] is False
    assert state["final_answer"] == "请说明需要查询的业务对象和时间范围。"


def test_low_confidence_intent_conservatively_clarifies() -> None:
    llm = FakeLLM(['{"intent":"data_query","confidence":0.4,"reason":"不确定"}', "请补充查询对象。"])
    graph = build_query_graph(
        database_executor=UnexpectedDatabaseAccess(),
        llm_client=llm,
        schema_retriever=UnexpectedRetriever(),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state("帮我看一下情况"))

    assert state["intent"] == QueryIntent.CLARIFICATION
    assert state["intent_source"] == "llm"
    assert state["intent_classification_valid"] is False
