from pathlib import Path

import pytest

from app.api.authorization import AccessPolicy
from app.db.sqlite_adapter import SQLiteAdapter
from app.demo import DEMO_TABLES
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
        allowed_tables=DEMO_TABLES,
        allowed_columns={},
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
        'SELECT COUNT(*) AS "数量" FROM "用户"',
        "用户数量为 1000。",
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
    assert state["query_result"].rows == [[1000]]
    assert state["final_answer"] == "用户数量为 1000。"
    assert len(llm.prompts) == 2
    assert state["answer_source"] == "result_summary"
    assert state["intent_source"] == "rule"


def test_result_summary_failure_keeps_safe_query_result() -> None:
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    llm = FakeLLM(
        ['SELECT COUNT(*) AS "数量" FROM "用户"', '{"valid": true}', RuntimeError("summary unavailable")]
    )
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=llm,
        schema_retriever=SQLiteSchemaRetriever(adapter),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state("查询用户数量"))

    assert state["status"] == "succeeded"
    assert state["query_result"].rows == [[1000]]
    assert state["final_answer"] == "查询完成，共返回 1 行结果。"
    assert state["answer_source"] == "deterministic_fallback"


def test_projection_review_repairs_broad_product_list_before_execution() -> None:
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    broad_sql = 'SELECT "编号", "商品名称", "商品编码", "供应商编号", "品牌" FROM "商品"'
    minimal_sql = 'SELECT "商品名称" FROM "商品"'
    llm = FakeLLM(
        [
            broad_sql,
            '{"valid": false, "reason": "名单查询只要求商品名称，不能返回商品编码、供应商编号或品牌。"}',
            minimal_sql,
            '{"valid": true}',
        ]
    )
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=llm,
        schema_retriever=SQLiteSchemaRetriever(adapter),
        access_policy=policy(),
        query_timeout_seconds=15,
        result_summary_enabled=False,
    )

    state = graph.invoke(
        create_initial_state(
            request_id="projection-repair",
            question="查询有哪些商品",
            database_id="demo",
            dialect="sqlite",
            max_iterations=2,
        )
    )

    assert state["status"] == "succeeded"
    assert state["generated_sql"] == minimal_sql
    assert state["query_result"].columns == ["商品名称"]
    assert state["query_result"].rows[0] == ["显示器 0001"]
    assert "名单查询只要求商品名称" in llm.prompts[2].to_string()
    assert [event.node for event in state["trace"]].count("review_sql_projection") == 2


@pytest.mark.parametrize(
    ("question", "sql", "columns"),
    [
        ("查询商品名称和销售价", 'SELECT "商品名称", "销售价" FROM "商品" LIMIT 2', ["商品名称", "销售价"]),
        ("查询商品品牌", 'SELECT "品牌" FROM "商品" LIMIT 2', ["品牌"]),
    ],
)
def test_projection_review_allows_fields_explicitly_requested(question: str, sql: str, columns: list[str]) -> None:
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    llm = FakeLLM([sql, '{"valid": true}'])
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=llm,
        schema_retriever=SQLiteSchemaRetriever(adapter),
        access_policy=policy(),
        query_timeout_seconds=15,
        result_summary_enabled=False,
    )

    state = graph.invoke(
        create_initial_state(
            request_id="projection-explicit-fields",
            question=question,
            database_id="demo",
            dialect="sqlite",
            max_iterations=1,
        )
    )

    assert state["status"] == "succeeded"
    assert state["query_result"].columns == columns


class NoExecuteAdapter:
    def __init__(self) -> None:
        self.schema_adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))

    def inspect_schema(self, database_id: str):
        return self.schema_adapter.inspect_schema(database_id)

    def get_schema_version(self, database_id: str) -> str:
        return self.schema_adapter.get_schema_version(database_id)

    def execute_readonly(self, *args, **kwargs):
        raise AssertionError("projection review failure must not execute SQL")


@pytest.mark.parametrize(
    "review_outcomes",
    [
        ['{"valid": "not a boolean"}'],
        [RuntimeError("projection reviewer unavailable")],
        [
            '{"valid": false, "reason": "名单查询包含未请求字段。"}',
            'SELECT "商品编码", "商品名称" FROM "商品"',
            '{"valid": false, "reason": "名单查询仍包含未请求字段。"}',
        ],
    ],
)
def test_projection_review_failure_never_executes_sql(review_outcomes: list[str | Exception]) -> None:
    adapter = NoExecuteAdapter()
    outcomes: list[str | Exception] = ['SELECT "商品编码", "商品名称" FROM "商品"', *review_outcomes]
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=FakeLLM(outcomes),
        schema_retriever=SQLiteSchemaRetriever(adapter),
        access_policy=policy(),
        query_timeout_seconds=15,
        result_summary_enabled=False,
    )

    state = graph.invoke(
        create_initial_state(
            request_id="projection-failure",
            question="查询有哪些商品",
            database_id="demo",
            dialect="sqlite",
            max_iterations=2,
        )
    )

    assert state["status"] == "failed"
    assert "query_result" not in state or state["query_result"] is None


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


def test_ambiguous_question_returns_clarification_without_database_access() -> None:
    llm = FakeLLM([])
    graph = build_query_graph(
        database_executor=UnexpectedDatabaseAccess(),
        llm_client=llm,
        schema_retriever=UnexpectedRetriever(),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state("帮我看看数据"))

    assert state["intent"] == QueryIntent.CLARIFY
    assert state["status"] == "needs_clarification"
    assert state["required_actions"] == ["provide_fields"]
    assert len(llm.prompts) == 0
    assert state["intent_source"] == "rule"


def test_invalid_intent_json_returns_clarification_without_database_access() -> None:
    llm = FakeLLM(["这看起来像数据问题"])
    graph = build_query_graph(
        database_executor=UnexpectedDatabaseAccess(),
        llm_client=llm,
        schema_retriever=UnexpectedRetriever(),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state("这个事情怎么处理"))

    assert state["intent"] == QueryIntent.CLARIFY
    assert state["status"] == "needs_clarification"
    assert state["intent_classification_valid"] is False


def test_low_confidence_intent_returns_clarification_without_database_access() -> None:
    llm = FakeLLM(['{"intent":"data_query","confidence":0.4,"reason":"不确定"}'])
    graph = build_query_graph(
        database_executor=UnexpectedDatabaseAccess(),
        llm_client=llm,
        schema_retriever=UnexpectedRetriever(),
        access_policy=policy(),
        query_timeout_seconds=15,
    )

    state = graph.invoke(initial_state("帮我看一下情况"))

    assert state["intent"] == QueryIntent.CLARIFY
    assert state["status"] == "needs_clarification"
    assert state["intent_source"] == "llm"
    assert state["intent_classification_valid"] is False
