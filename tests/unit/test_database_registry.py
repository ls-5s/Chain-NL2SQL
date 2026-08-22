from fastapi.testclient import TestClient

from app.api import dependencies, routes
from app.config.settings import get_settings
from app.db.registry import DatabaseRegistry
from app.main import create_app


def _configure(monkeypatch, tmp_path):
    monkeypatch.setenv("CONVERSATION_DATABASE_PATH", str(tmp_path / "app.sqlite3"))
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "123456")
    monkeypatch.setenv("ALLOWED_DATABASE_IDS", "demo")
    get_settings.cache_clear()
    dependencies._registries.clear()
    routes._conversation_repositories.clear()


def test_registry_seeds_demo_and_keeps_new_tables_disabled(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    settings = get_settings()
    registry = DatabaseRegistry(settings.conversation_database_path, settings)
    assert registry.allowed_tables("demo") == {"users", "products", "orders", "order_items"}
    registry.sync_tables("demo", ["users", "new_table"])
    assert registry.allowed_tables("demo") == {"users"}
    registry.set_table_access("demo", "new_table", True)
    assert registry.allowed_tables("demo") == {"users", "new_table"}


def test_database_api_lists_and_updates_table_access(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    client = TestClient(create_app())
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200

    response = client.get("/api/v1/databases")
    assert response.status_code == 200
    assert response.json()["database_ids"] == ["demo"]
    assert any(table["agent_access"] for table in response.json()["databases"][0]["tables"])

    response = client.patch("/api/v1/databases/demo/tables/users", json={"agent_access": False})
    assert response.status_code == 200
    assert response.json()["agent_access"] is False
    assert client.get("/api/v1/databases/demo/tables").json()[0]["table_name"] == "order_items"
