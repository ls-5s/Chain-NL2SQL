from fastapi.testclient import TestClient

from app.api import routes
from app.config.settings import get_settings
from app.db.registry import DatabaseRegistry
from app.main import create_app


def test_health_reports_environment() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["environment"] == "local"


def test_query_reports_missing_llm_configuration(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "123456")
    get_settings.cache_clear()

    client = TestClient(create_app())
    login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"})
    assert login.status_code == 200
    response = client.post(
        "/api/v1/query",
        json={"question": "查询用户数量", "database_id": "demo"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "LLM service is not configured."


def test_conversation_runtime_failure_finishes_turn(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CONVERSATION_DATABASE_PATH", str(tmp_path / "conversations.sqlite3"))
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "123456")
    get_settings.cache_clear()
    routes._conversation_repositories.clear()

    def fail_runtime(*args, **kwargs):
        raise RuntimeError("api_key=sk-secret-value provider unavailable")

    monkeypatch.setattr(routes, "_create_graph_runtime", fail_runtime)
    client = TestClient(create_app())
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    conversation = client.post("/api/v1/conversations", json={"database_id": "demo"}).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/query",
        json={"question": "你好"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "The NL2SQL agent could not complete the query."
    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert detail["messages"][-1]["status"] == "failed"
    assert "sk-secret-value" not in detail["messages"][-1]["content"]


def test_mysql_conversation_uses_registered_dialect(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CONVERSATION_DATABASE_PATH", str(tmp_path / "conversations.sqlite3"))
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "123456")
    get_settings.cache_clear()
    routes._conversation_repositories.clear()

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
    registry.set_table_access(record.id, "users", True)

    captured: dict[str, object] = {}

    class FakeGraph:
        async def astream(self, state, stream_mode):
            captured.update(state)
            yield {"finalize": {"status": "succeeded", "final_answer": "ok"}}

    class FakeDatabase:
        def close(self) -> None:
            return None

    monkeypatch.setattr(
        routes,
        "_create_graph_runtime",
        lambda settings, context, database_id: (FakeGraph(), FakeDatabase(), "mysql"),
    )

    client = TestClient(create_app())
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    conversation = client.post("/api/v1/conversations", json={"database_id": "external-mysql"}).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/query",
        json={"question": "查询用户数量"},
    )

    assert response.status_code == 200
    assert "event: complete" in response.text
    assert captured["dialect"] == "mysql"
