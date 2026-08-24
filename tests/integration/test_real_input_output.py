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
        "SELECT COUNT(*) AS user_count FROM users",
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
    assert sql_complete["result"]["rows"] == [[3]]
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
