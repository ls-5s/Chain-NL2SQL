from fastapi.testclient import TestClient

from app.api import auth
from app.config.settings import get_settings
from app.main import create_app


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("CONVERSATION_DATABASE_PATH", str(tmp_path / "members.sqlite3"))
    monkeypatch.setenv("APP_AUTH_USERNAME", "admin")
    monkeypatch.setenv("APP_AUTH_PASSWORD", "123456")
    get_settings.cache_clear()
    auth._repositories.clear()
    return TestClient(create_app())


def test_admin_can_manage_members_without_exposing_password(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200

    created = client.post("/api/v1/members", json={"username": "alice", "password": "password"})
    assert created.status_code == 201
    assert "password" not in created.json()
    assert "password_hash" not in created.json()

    duplicate = client.post("/api/v1/members", json={"username": "alice", "password": "password"})
    assert duplicate.status_code == 409

    admin = client.get("/api/v1/members")
    assert admin.status_code == 200
    assert all("password" not in item and "password_hash" not in item for item in admin.json())


def test_member_can_read_but_cannot_write_members(monkeypatch, tmp_path) -> None:
    admin_client = _client(monkeypatch, tmp_path)
    assert admin_client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    created = admin_client.post("/api/v1/members", json={"username": "alice", "password": "password"}).json()

    member_client = TestClient(create_app())
    assert member_client.post("/api/v1/auth/login", json={"username": "alice", "password": "password"}).status_code == 200
    assert member_client.get("/api/v1/members").status_code == 200
    assert member_client.post("/api/v1/members", json={"username": "bob", "password": "password"}).status_code == 403
    assert member_client.patch(f"/api/v1/members/{created['id']}", json={"password": "new-password"}).status_code == 403
    assert member_client.delete(f"/api/v1/members/{created['id']}").status_code == 403


def test_super_admin_cannot_be_deleted(monkeypatch, tmp_path) -> None:
    client = _client(monkeypatch, tmp_path)
    assert client.post("/api/v1/auth/login", json={"username": "admin", "password": "123456"}).status_code == 200
    response = client.delete("/api/v1/members/single-user")
    assert response.status_code == 400
