from __future__ import annotations

from pathlib import Path

from app.api.authorization import AccessPolicy
from app.conversations.repository import ConversationRepository
from app.db.sqlite_adapter import SQLiteAdapter
from app.demo import DEMO_TABLES
from app.graph.builder import build_query_graph
from app.graph.state import create_initial_state
from app.knowledge.service import KnowledgeStore
from app.rag.index_manager import SchemaIndexManager
from app.rag.retriever import SchemaRetrievalRequest
from app.schemas.domain import QueryStatus
from app.schemas.response import QueryResponse
from scripts.init_demo_db import initialize
from scripts.seed_demo_knowledge import seed
from tests.fakes.fake_llm import FakeLLM


ROOT = Path(__file__).resolve().parents[2]
def _policy() -> AccessPolicy:
    return AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=DEMO_TABLES,
        allowed_columns={},
    )


def test_seeded_demo_database_and_schema_rag_drive_sql(tmp_path: Path) -> None:
    database_path = tmp_path / "demo.sqlite"
    initialize(database_path, ROOT / "data" / "fixtures" / "demo.sql")
    adapter = SQLiteAdapter("demo", str(database_path))
    manager = SchemaIndexManager(adapter.inspect_schema, root=tmp_path / "schema", mode="bm25")
    llm = FakeLLM('SELECT COUNT(*) AS "用户数量" FROM "用户"')
    graph = build_query_graph(
        database_executor=adapter,
        llm_client=llm,
        schema_retriever=manager,
        access_policy=_policy(),
        query_timeout_seconds=5,
        result_summary_enabled=False,
    )

    result = graph.invoke(
        create_initial_state(
            request_id="demo-rag-sql",
            question="查询用户数量",
            database_id="demo",
            dialect="sqlite",
            max_iterations=1,
        )
    )

    assert result["status"] == QueryStatus.SUCCEEDED
    assert result["retrieval_mode"] == "bm25"
    assert "用户" in result["retrieved_tables"]
    assert result["query_result"].rows == [[1000]]
    assert "销售额" not in str(llm.prompts[0])


def test_seeded_business_knowledge_is_grounded_and_persisted(tmp_path: Path) -> None:
    database_path = tmp_path / "knowledge.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    seeded = seed(database_path, knowledge_root, ROOT / "data" / "knowledge_sources")
    assert {item["filename"] for item in seeded} == {
        "sales_metrics.md",
        "order_rules.md",
        "demo_dictionary.md",
        "inventory_rules.md",
        "payment_fulfillment_rules.md",
        "marketing_service_rules.md",
        "loyalty_rules.md",
    }
    store = KnowledgeStore(database_path, knowledge_root, workers=1)
    try:
        hits = store.retrieve("销售额怎么算", user_id="member-1", role="member")
        assert hits
        sales_hit = next(item for item in hits if item.title == "sales_metrics.md")
        rules_hits = store.retrieve("待支付订单是否计入销售额", user_id="member-1", role="member")
        assert any(item.title == "order_rules.md" for item in rules_hits)
        assert any(item.title == "inventory_rules.md" for item in store.retrieve("仓库库存怎么算", user_id="member-1", role="member"))
        assert any(item.title == "payment_fulfillment_rules.md" for item in store.retrieve("退款完成状态", user_id="member-1", role="member"))
        assert any(item.title == "loyalty_rules.md" for item in store.retrieve("会员积分流水", user_id="member-1", role="member"))
        assert store.get_acl(sales_hit.document_id)["policy_type"] == "all_authenticated"

        answer = f"销售额默认统计已支付订单。[{sales_hit.document_id}]"
        graph = build_query_graph(
            database_executor=SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite")),
            llm_client=FakeLLM(answer),
            schema_retriever=SchemaIndexManager(
                SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite")).inspect_schema,
                root=tmp_path / "schema",
                mode="bm25",
            ),
            access_policy=_policy(),
            query_timeout_seconds=5,
            result_summary_enabled=False,
            knowledge_retriever=lambda question, top_k: store.retrieve(
                question, top_k, user_id="member-1", role="member"
            ),
        )
        result = graph.invoke(
            create_initial_state(
                request_id="demo-rag-knowledge",
                question="公司制度中的销售额口径是什么",
                max_iterations=1,
            )
        )
        assert result["status"] == QueryStatus.SUCCEEDED
        assert result["knowledge_hits"]
        assert sales_hit.document_id in result["final_answer"]
        assert result["answer_source"] == "general_llm"

        repository = ConversationRepository(tmp_path / "conversations.sqlite3")
        conversation = repository.create_conversation("member-1", None)
        turn = repository.start_turn("member-1", conversation["id"], "销售额口径", "")
        response = QueryResponse(
            request_id="demo-rag-knowledge",
            intent="general_chat",
            status="succeeded",
            iteration=0,
            final_answer=result["final_answer"],
            answer_source="general_llm",
            knowledge_hits=result["knowledge_hits"],
        )
        repository.finish_turn(turn["turn_id"], turn["assistant_message_id"], response)
        detail = repository.get_conversation("member-1", conversation["id"])
        assert detail["messages"][-1]["response"].knowledge_hits[0].document_id == sales_hit.document_id
        assert detail["messages"][-1]["status"] == "succeeded"
    finally:
        store.close()
