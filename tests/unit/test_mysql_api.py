from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.api import dependencies, routes
from app.config.settings import get_settings
from app.db.registry import DatabaseRegistry
from app.main import create_app
from app.schemas.domain import QueryResult, SchemaDocument, SchemaRetrieval
from tests.fakes.fake_llm import FakeLLM


def _configure(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CONVERSATION_DATABASE_PATH", str(tmp_path / "conversations.sqlite3"))
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "123456")
    monkeypatch.setenv("SCHEMA_RETRIEVAL_MODE", "bm25")
    monkeypatch.setenv("SCHEMA_INDEX_ROOT", str(tmp_path / "schema"))
    get_settings.cache_clear()
    dependencies._registries.clear()
    routes._conversation_repositories.clear()


class FakeMySQL:
    def __init__(self) -> None:
        self.execute_calls = 0

    def inspect_schema(self, database_id: str) -> SchemaRetrieval:
        return SchemaRetrieval(
            documents=[
                SchemaDocument(
                    table_name="user",
                    content="TABLE user\nCOLUMNS id INT, name VARCHAR\nPRIMARY KEY id\nFOREIGN KEYS none",
                    database_id=database_id,
                    column_names=["id", "name"],
                    dialect="mysql",
                )
            ],
            schema_version="mysql-test-v1",
            retrieval_mode="full_schema",
        )

    def get_schema_version(self, database_id: str) -> str:
        return "mysql-test-v1"

    def execute_readonly(self, sql, deadline, access_policy, parameters=()):
        self.execute_calls += 1
        return QueryResult(columns=["count"], rows=[[5]], row_count=1)

    def close(self) -> None:
        return None


def _client_and_registry(monkeypatch, tmp_path, *, table_access: bool):
    _configure(monkeypatch, tmp_path)
    settings = get_settings()
    registry = DatabaseRegistry(settings.conversation_database_path, settings)
    record = registry.create(
        name="External MySQL",
        dialect="mysql",
        config={
            "host": "127.0.0.1",
            "port": 3306,
            "database": "demo",
            "username": "readonly",
            "credential_ref": "local/mysql",
            "tls": True,
        },
    )
    registry.sync_tables(record.id, ["user"])
    registry.set_table_access(record.id, "user", table_access)
    database = FakeMySQL()
    monkeypatch.setattr(routes, "_adapter_for_registration", lambda record, settings: database)
    monkeypatch.setattr(routes, "create_openai_client", lambda settings: FakeLLM(["SELECT COUNT(*) AS count FROM user"]))
    client = TestClient(create_app())
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    return client, database


def _complete_event(response_text: str) -> dict[str, object]:
    for chunk in response_text.split("\n\n"):
        if chunk.startswith("event: complete"):
            return json.loads(chunk.split("\ndata: ", 1)[1])
    raise AssertionError("SSE complete event was not emitted")


def test_mysql_query_returns_complete_result_for_authorized_table(monkeypatch, tmp_path) -> None:
    client, database = _client_and_registry(monkeypatch, tmp_path, table_access=True)

    response = client.post("/api/v1/query", json={"database_id": "external-mysql", "question": "查询用户数量"})
    payload = _complete_event(response.text)

    assert response.status_code == 200
    assert payload["status"] == "succeeded"
    assert payload["result"]["rows"] == [[5]]
    assert payload["generated_sql"] == "SELECT COUNT(*) AS count FROM user"
    assert database.execute_calls == 1


def test_mysql_query_fails_closed_for_unauthorized_table(monkeypatch, tmp_path) -> None:
    client, database = _client_and_registry(monkeypatch, tmp_path, table_access=False)

    response = client.post("/api/v1/query", json={"database_id": "external-mysql", "question": "查询用户数量"})
    payload = _complete_event(response.text)

    assert response.status_code == 200
    assert payload["status"] == "failed"
    assert payload["error_category"] == "schema_retrieval_error"
    assert payload["result"] is None
    assert database.execute_calls == 0
