from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import create_app


def test_health_reports_environment() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["environment"] == "local"


def test_query_reports_missing_llm_configuration(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    get_settings.cache_clear()

    response = TestClient(create_app()).post(
        "/api/v1/query",
        json={"question": "查询用户数量", "database_id": "demo"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "LLM service is not configured."
