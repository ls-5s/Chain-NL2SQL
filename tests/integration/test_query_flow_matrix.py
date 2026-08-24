from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import auth, dependencies, routes
from app.config.settings import get_settings
from app.knowledge.service import KnowledgeStore
from app.main import create_app
from scripts.init_demo_db import initialize
from scripts.seed_demo_knowledge import seed
from tests.fakes.fake_llm import FakeLLM


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "evals" / "query_flow_dataset.jsonl"


def _records() -> list[dict[str, object]]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sse_events(body: str) -> list[tuple[str, dict[str, object]]]:
    events = []
    for chunk in body.strip().split("\n\n"):
        lines = chunk.splitlines()
        if len(lines) >= 2 and lines[0].startswith("event: ") and lines[1].startswith("data: "):
            events.append((lines[0][7:], json.loads(lines[1][6:])))
    return events


def _classification_response() -> str:
    return json.dumps({"intent": "data_query", "confidence": 0.99, "reason": "测试数据查询"}, ensure_ascii=False)


def _sql_for(scenario: str) -> str:
    return {
        "count_users": "SELECT COUNT(*) AS count FROM users",
        "count_orders": "SELECT COUNT(*) AS count FROM orders",
        "product_fields": "SELECT name, category FROM products ORDER BY id",
        "paid_orders": "SELECT id FROM orders WHERE status = 'paid' ORDER BY id",
        "large_orders": "SELECT id FROM orders WHERE total_amount > 300",
        "order_aggregates": "SELECT AVG(total_amount), SUM(total_amount) FROM orders",
        "status_counts": "SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY COUNT(*) DESC, status",
        "order_users": "SELECT orders.id, users.name FROM orders JOIN users ON orders.user_id = users.id ORDER BY orders.id",
        "product_quantities": "SELECT products.name, SUM(order_items.quantity) FROM products JOIN order_items ON products.id = order_items.product_id GROUP BY products.id, products.name ORDER BY products.id",
        "top_products": "SELECT name, price FROM products ORDER BY price DESC LIMIT 2",
        "recent_orders": "SELECT id FROM orders WHERE created_at >= '2026-01-01' ORDER BY id",
        "empty_orders": "SELECT id FROM orders WHERE status = 'cancelled'",
        "masked_email": "SELECT name, email FROM users ORDER BY id",
        "unknown_column_repair": "SELECT missing_column FROM users",
        "multiple_statements": "SELECT id FROM users; SELECT id FROM orders",
        "delete_sql": "DELETE FROM users",
        "dangerous_function": "SELECT readfile('secret.txt') FROM users",
        "system_table": "SELECT name FROM sqlite_master",
        "comment_sql": "SELECT id FROM users -- bypass",
        "unknown_table": "SELECT id FROM missing_table",
        "pragma_sql": "PRAGMA user_version",
        "attach_sql": "ATTACH DATABASE 'other.sqlite' AS other",
        "update_sql": "UPDATE users SET name = 'x'",
        "drop_sql": "DROP TABLE users",
    }[scenario]


def _llm_outcomes(record: dict[str, object], document_id: str) -> list[str | Exception]:
    category = record["category"]
    scenario = record["scenario"]
    if scenario == "missing_database" or category == "clarify":
        return []
    if category == "general_chat":
        return ["这是一个通用回答。"]
    if category == "knowledge":
        if scenario == "knowledge_no_hit":
            return []
        if scenario == "knowledge_bad_citation":
            return ["这是回答，但没有提供资料引用。"]
        return [f"这是基于业务资料的回答。[{document_id}]"]
    if scenario in {"empty_sql", "invalid_sql_output"}:
        return [_classification_response(), ""]
    if scenario in {"system_table", "unknown_table", "multiple_statements", "delete_sql", "dangerous_function", "comment_sql", "pragma_sql", "attach_sql", "update_sql", "drop_sql"}:
        # These questions are deterministically classified as data queries by
        # the rule gate, so the first model call is SQL generation itself.
        return [_sql_for(scenario)]
    if scenario == "unknown_column_repair":
        return [_sql_for(scenario), "SELECT COUNT(*) AS count FROM users"]
    return [_sql_for(scenario)]


def _create_runtime(monkeypatch, tmp_path: Path, llm: FakeLLM) -> TestClient:
    database_path = tmp_path / "demo.sqlite"
    knowledge_database_path = tmp_path / "knowledge.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    if not database_path.exists():
        initialize(database_path, ROOT / "data" / "fixtures" / "demo.sql")
    if not knowledge_database_path.exists():
        seed(knowledge_database_path, knowledge_root, ROOT / "data" / "knowledge_sources")
    monkeypatch.setenv("DEMO_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("KNOWLEDGE_DATABASE_PATH", str(knowledge_database_path))
    monkeypatch.setenv("KNOWLEDGE_ROOT", str(knowledge_root))
    monkeypatch.setenv("SCHEMA_INDEX_ROOT", str(tmp_path / "schema_metadata"))
    monkeypatch.setenv("SCHEMA_RETRIEVAL_MODE", "bm25")
    monkeypatch.setenv("SCHEMA_FALLBACK_MODE", "bm25")
    monkeypatch.setenv("RESULT_SUMMARY_ENABLED", "false")
    monkeypatch.setenv("CONVERSATION_DATABASE_PATH", str(tmp_path / "conversations.sqlite3"))
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "123456")
    get_settings.cache_clear()
    auth._repositories.clear()
    dependencies._registries.clear()
    routes._conversation_repositories.clear()
    monkeypatch.setattr(routes, "create_openai_client", lambda settings: llm)
    client = TestClient(create_app())
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    return client


@pytest.mark.parametrize("record", _records(), ids=lambda record: str(record["scenario"]))
def test_user_question_matrix_through_http_and_persistence(monkeypatch, tmp_path: Path, record: dict[str, object]) -> None:
    seed_database = tmp_path / "knowledge.sqlite3"
    seed_root = tmp_path / "knowledge"
    seed(seed_database, seed_root, ROOT / "data" / "knowledge_sources")
    store = KnowledgeStore(seed_database, seed_root, workers=1)
    try:
        hits = store.retrieve("销售额怎么算", user_id="admin", role="super_admin")
        document_titles = {
            "knowledge_rules": "order_rules.md",
            "knowledge_dictionary": "demo_dictionary.md",
        }
        target_title = document_titles.get(str(record["scenario"]), "sales_metrics.md")
        document_id = next(item.document_id for item in hits if item.title == target_title)
    finally:
        store.close()

    llm = FakeLLM(_llm_outcomes(record, document_id))
    client = _create_runtime(monkeypatch, tmp_path, llm)
    database_id = record.get("database_id")
    conversation = client.post("/api/v1/conversations", json={"database_id": database_id}).json()
    conversation_id = conversation["id"]
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/query",
        json={"question": record["question"], "client_request_id": f"matrix-{record['scenario']}"},
    )
    assert response.status_code == 200
    events = _sse_events(response.text)
    assert events
    assert sum(name == "start" for name, _ in events) == 1
    assert all(data["request_id"] == events[0][1]["request_id"] for _, data in events)
    terminal = [item for item in events if item[0] in {"complete", "error"}]
    assert len(terminal) == 1
    complete_name, complete = terminal[0]
    if record["expected_status"] in {"failed", "blocked"}:
        assert complete_name in {"complete", "error"}, response.text
        if complete_name == "error":
            assert "The NL2SQL agent could not complete the query." in response.text
    else:
        assert complete_name == "complete", response.text
    assert complete["intent"] == record["expected_intent"]
    assert complete["status"] == record["expected_status"]
    progress_nodes = {data.get("node") for name, data in events if name == "progress"}
    assert set(record["expected_nodes"]).issubset(progress_nodes | {"complete"})
    if record.get("expected_result") is not None:
        assert complete["result"]["rows"] == record["expected_result"]
    if record["category"] == "knowledge" and record["scenario"] in {"knowledge_metrics", "knowledge_rules", "knowledge_dictionary"}:
        assert document_id in complete["final_answer"]
    if record["category"] in {"general_chat", "clarify", "knowledge"}:
        assert not ("retrieve_schema" in progress_nodes or "execute_sql" in progress_nodes)

    detail = client.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.status_code == 200
    assistant = detail.json()["messages"][-1]
    assert assistant["status"] == record["expected_status"]
    assert assistant["response"]["status"] == record["expected_status"]


@pytest.mark.parametrize("payload", [{"question": ""}, {"question": "x" * 2001}, {"question": "你好", "max_iterations": 11}])
def test_invalid_user_input_is_rejected_before_agent(monkeypatch, tmp_path: Path, payload: dict[str, object]) -> None:
    client = _create_runtime(monkeypatch, tmp_path, FakeLLM([]))
    conversation = client.post("/api/v1/conversations", json={"database_id": None}).json()
    response = client.post(f"/api/v1/conversations/{conversation['id']}/query", json=payload)
    assert response.status_code == 422


def test_http_retry_with_same_client_request_id_reuses_persisted_turn(monkeypatch, tmp_path: Path) -> None:
    """A browser retry must not create a second assistant turn or run the LLM twice."""

    llm = FakeLLM(["这是一次确定性的回答。"])
    client = _create_runtime(monkeypatch, tmp_path, llm)
    conversation = client.post("/api/v1/conversations", json={"database_id": "demo"}).json()
    conversation_id = conversation["id"]
    payload = {"question": "你好", "client_request_id": "matrix-idempotent-1"}

    first = client.post(f"/api/v1/conversations/{conversation_id}/query", json=payload)
    second = client.post(f"/api/v1/conversations/{conversation_id}/query", json=payload)
    first_complete = next(data for name, data in _sse_events(first.text) if name == "complete")
    second_complete = next(data for name, data in _sse_events(second.text) if name == "complete")
    assert first_complete["status"] == second_complete["status"] == "succeeded"
    assert first_complete["final_answer"] == second_complete["final_answer"]
    assert len(llm.prompts) == 1
    detail = client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert len([message for message in detail["messages"] if message["role"] == "assistant"]) == 1


@pytest.mark.parametrize("mode", ["acl_denied", "retrieval_error"])
def test_http_knowledge_fail_closed_for_acl_and_retrieval_errors(monkeypatch, tmp_path: Path, mode: str) -> None:
    """Unauthorized or unavailable knowledge never falls through to SQL."""

    knowledge_database = tmp_path / "knowledge.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    seed(knowledge_database, knowledge_root, ROOT / "data" / "knowledge_sources")
    if mode == "acl_denied":
        store = KnowledgeStore(knowledge_database, knowledge_root, workers=1)
        try:
            for item in store.list():
                store.set_acl(item["id"], "deny")
        finally:
            store.close()
    if mode == "retrieval_error":
        monkeypatch.setattr(
            routes,
            "_authorized_knowledge_retriever",
            lambda settings, context: lambda *_args: (_ for _ in ()).throw(RuntimeError("retrieval failed")),
        )
    client = _create_runtime(monkeypatch, tmp_path, FakeLLM([]))
    conversation = client.post("/api/v1/conversations", json={"database_id": "demo"}).json()
    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/query",
        json={"question": "公司制度中的销售额口径是什么", "client_request_id": f"knowledge-{mode}"},
    )
    events = _sse_events(response.text)
    complete = next(data for name, data in events if name == "complete")
    nodes = {data.get("node") for name, data in events if name == "progress"}
    assert complete["status"] == "no_grounded_answer"
    assert {"retrieve_knowledge", "grounded_answer"}.issubset(nodes)
    assert "retrieve_schema" not in nodes
    assert "execute_sql" not in nodes
