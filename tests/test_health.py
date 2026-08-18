from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_environment() -> None:
    # 健康检查必须可在未配置模型和数据库时独立验证服务框架。
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["environment"] == "local"


def test_query_is_explicitly_not_implemented() -> None:
    # 骨架阶段应显式拒绝查询，而不是返回伪造成功结果。
    response = TestClient(create_app()).post(
        "/api/v1/query",
        json={"question": "查询用户数量", "database_id": "demo"},
    )

    assert response.status_code == 501
