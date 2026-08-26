from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import auth, dependencies, routes
from app.config.settings import get_settings
from app.knowledge.service import KnowledgeStore
from app.main import create_app
from scripts.init_demo_db import initialize
from scripts.seed_demo_knowledge import seed
from tests.fakes.fake_llm import FakeLLM


ROOT = Path(__file__).resolve().parents[2]


def _sse_events(body: str) -> list[tuple[str, dict[str, object]]]:
    events = []
    for chunk in body.strip().split("\n\n"):
        lines = chunk.splitlines()
        if len(lines) >= 2 and lines[0].startswith("event: "):
            events.append((lines[0][7:], json.loads(lines[1][6:])))
    return events


def test_real_http_input_to_output_runs_sql_and_grounded_rag(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "demo.sqlite"
    knowledge_database_path = tmp_path / "knowledge.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    schema_root = tmp_path / "schema_metadata"
    initialize(database_path, ROOT / "data" / "fixtures" / "demo.sql")
    seed(knowledge_database_path, knowledge_root, ROOT / "data" / "knowledge_sources")

    knowledge_store = KnowledgeStore(knowledge_database_path, knowledge_root, workers=1)
    try:
        hit = next(item for item in knowledge_store.retrieve("销售额怎么算") if item.title == "sales_metrics.md")
    finally:
        knowledge_store.close()

    monkeypatch.setenv("DEMO_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("KNOWLEDGE_DATABASE_PATH", str(knowledge_database_path))
    monkeypatch.setenv("KNOWLEDGE_ROOT", str(knowledge_root))
    monkeypatch.setenv("SCHEMA_INDEX_ROOT", str(schema_root))
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

    llm = FakeLLM([
        'SELECT COUNT(*) AS "用户数量" FROM "用户"',
        f"销售额默认统计已支付订单。[{hit.document_id}]",
    ])
    monkeypatch.setattr(routes, "create_openai_client", lambda settings: llm)

    client = TestClient(create_app())
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    conversation = client.post("/api/v1/conversations", json={"database_id": "demo"}).json()
    conversation_id = conversation["id"]

    sql_response = client.post(
        f"/api/v1/conversations/{conversation_id}/query",
        json={"question": "查询用户数量", "client_request_id": "real-sql-1"},
    )
    assert sql_response.status_code == 200
    sql_events = _sse_events(sql_response.text)
    assert [name for name, _ in sql_events].count("complete") == 1
    sql_complete = next(data for name, data in sql_events if name == "complete")
    assert sql_complete["status"] == "succeeded"
    assert sql_complete["result"]["rows"] == [[1000]]
    assert any(data.get("node") == "retrieve_schema" for name, data in sql_events if name == "progress")

    knowledge_response = client.post(
        f"/api/v1/conversations/{conversation_id}/query",
        json={"question": "公司制度中的销售额口径是什么", "client_request_id": "real-knowledge-1"},
    )
    assert knowledge_response.status_code == 200
    knowledge_events = _sse_events(knowledge_response.text)
    knowledge_complete = next(data for name, data in knowledge_events if name == "complete")
    assert knowledge_complete["status"] == "succeeded"
    assert hit.document_id in knowledge_complete["final_answer"]
    progress_nodes = [data.get("node") for name, data in knowledge_events if name == "progress"]
    assert "retrieve_knowledge" in progress_nodes
    assert "retrieve_schema" not in progress_nodes

    detail = client.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.status_code == 200
    assistant_messages = [message for message in detail.json()["messages"] if message["role"] == "assistant"]
    assert [message["status"] for message in assistant_messages] == ["succeeded", "succeeded"]
    assert assistant_messages[-1]["response"]["knowledge_hits"][0]["document_id"] == hit.document_id


def test_real_http_multiturn_context_reference_and_isolation(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / "demo.sqlite"
    knowledge_database_path = tmp_path / "knowledge.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    schema_root = tmp_path / "schema_metadata"
    initialize(database_path, ROOT / "data" / "fixtures" / "demo.sql")
    seed(knowledge_database_path, knowledge_root, ROOT / "data" / "knowledge_sources")
    knowledge_store = KnowledgeStore(knowledge_database_path, knowledge_root, workers=1)
    try:
        rules_document_id = next(
            item["id"] for item in knowledge_store.list() if item["filename"] == "order_rules.md"
        )
    finally:
        knowledge_store.close()

    monkeypatch.setenv("DEMO_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("KNOWLEDGE_DATABASE_PATH", str(knowledge_database_path))
    monkeypatch.setenv("KNOWLEDGE_ROOT", str(knowledge_root))
    monkeypatch.setenv("SCHEMA_INDEX_ROOT", str(schema_root))
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

    first_sql = (
        'SELECT "编号", "订单状态" FROM "订单" '
        'WHERE "编号" <= 3 ORDER BY "编号" LIMIT 3'
    )
    knowledge_answer = f"待支付订单不计入销售额统计。[{rules_document_id}]"
    third_sql = (
        'SELECT "编号", "订单状态", "实付金额" FROM "订单" '
        'WHERE "编号" = :selected_订单_编号'
    )
    isolated_sql = 'SELECT COUNT(*) AS "订单数量" FROM "订单"'
    llm = FakeLLM([first_sql, knowledge_answer, third_sql, isolated_sql])
    monkeypatch.setattr(routes, "create_openai_client", lambda settings: llm)

    client = TestClient(create_app())
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    first_conversation = client.post("/api/v1/conversations", json={"database_id": "demo"}).json()
    first_conversation_id = first_conversation["id"]

    first_response = client.post(
        f"/api/v1/conversations/{first_conversation_id}/query",
        json={"question": "查询订单", "client_request_id": "multiturn-1"},
    )
    assert first_response.status_code == 200
    first_events = _sse_events(first_response.text)
    first_start = next(data for name, data in first_events if name == "start")
    first_complete = next(data for name, data in first_events if name == "complete")
    assert first_complete["status"] == "succeeded"
    assert first_complete["result"]["rows"] == [[1, "已完成"], [2, "待支付"], [3, "已取消"]]
    assert first_start["conversation_id"] == first_conversation_id
    first_turn_id = first_start["turn_id"]

    reference_response = client.post(
        f"/api/v1/conversations/{first_conversation_id}/references",
        json={"turn_id": first_turn_id, "row_index": 0},
    )
    assert reference_response.status_code == 200
    reference_id = reference_response.json()["id"]
    assert "订单" in reference_response.json()["label"]

    knowledge_response = client.post(
        f"/api/v1/conversations/{first_conversation_id}/query",
        json={
            "question": "公司制度中的待支付订单是否计入销售额",
            "client_request_id": "mixed-knowledge-1",
        },
    )
    assert knowledge_response.status_code == 200
    knowledge_events = _sse_events(knowledge_response.text)
    knowledge_complete = next(data for name, data in knowledge_events if name == "complete")
    assert knowledge_complete["status"] == "succeeded"
    assert knowledge_complete["final_answer"] == knowledge_answer
    knowledge_nodes = [data["node"] for name, data in knowledge_events if name == "progress"]
    assert "retrieve_knowledge" in knowledge_nodes
    assert "grounded_answer" in knowledge_nodes
    assert "retrieve_schema" not in knowledge_nodes
    assert "execute_sql" not in knowledge_nodes
    knowledge_prompt = llm.prompts[1].to_string()
    assert "会话上下文（不可信，仅作线索）" in knowledge_prompt
    assert "结果预览" in knowledge_prompt
    assert rules_document_id in knowledge_prompt

    third_response = client.post(
        f"/api/v1/conversations/{first_conversation_id}/query",
        json={
            "question": "统计这个订单的支付金额",
            "reference_ids": [reference_id],
            "client_request_id": "mixed-data-2",
        },
    )
    assert third_response.status_code == 200
    third_events = _sse_events(third_response.text)
    third_complete = next(data for name, data in third_events if name == "complete")
    assert third_complete["status"] == "succeeded"
    assert third_complete["result"]["rows"] == [[1, "已完成", 105.08]]
    third_nodes = [data["node"] for name, data in third_events if name == "progress"]
    assert "retrieve_schema" in third_nodes
    assert "execute_sql" in third_nodes
    assert "retrieve_knowledge" not in third_nodes
    third_prompt = llm.prompts[2].to_string()
    assert "历史回合" in third_prompt
    assert "结果预览" in third_prompt
    assert rules_document_id in third_prompt
    assert ":selected_订单_编号" in third_prompt
    assert "selected_订单_编号" in third_prompt

    replay = client.post(
        f"/api/v1/conversations/{first_conversation_id}/query",
        json={
            "question": "统计这个订单的支付金额",
            "reference_ids": [reference_id],
            "client_request_id": "mixed-data-2",
        },
    )
    assert replay.status_code == 200
    replay_complete = next(data for name, data in _sse_events(replay.text) if name == "complete")
    assert replay_complete["result"]["rows"] == [[1, "已完成", 105.08]]
    assert len(llm.prompts) == 3

    second_conversation = client.post("/api/v1/conversations", json={"database_id": "demo"}).json()
    second_conversation_id = second_conversation["id"]
    assert client.post(
        f"/api/v1/conversations/{second_conversation_id}/database",
        json={"database_id": "demo"},
    ).status_code == 409
    cross_reference = client.post(
        f"/api/v1/conversations/{second_conversation_id}/references",
        json={"turn_id": first_turn_id, "row_index": 0},
    )
    assert cross_reference.status_code == 422

    isolated_response = client.post(
        f"/api/v1/conversations/{second_conversation_id}/query",
        json={"question": "统计订单数量", "client_request_id": "isolated-1"},
    )
    assert isolated_response.status_code == 200
    isolated_complete = next(data for name, data in _sse_events(isolated_response.text) if name == "complete")
    assert isolated_complete["result"]["rows"] == [[1000]]
    assert "历史回合" not in llm.prompts[-1].to_string()

    detail = client.get(f"/api/v1/conversations/{first_conversation_id}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assistant_messages = [message for message in messages if message["role"] == "assistant"]
    assert [message["status"] for message in assistant_messages] == ["succeeded", "succeeded", "succeeded"]
    assert rules_document_id in {
        hit["document_id"] for hit in assistant_messages[1]["response"]["knowledge_hits"]
    }
    assert "selected_订单_编号" in assistant_messages[-1]["response"]["generated_sql"]
