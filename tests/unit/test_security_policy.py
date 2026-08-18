from __future__ import annotations

import pytest

pytest.importorskip("sqlglot")

from app.api.authorization import AccessPolicy
from app.db.security_policy import validate_readonly_sql


@pytest.fixture
def policy() -> AccessPolicy:
    # 单元测试使用比完整演示策略更小的策略，便于验证拒绝逻辑。
    return AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=frozenset({"users", "orders"}),
        allowed_columns={
            "users": frozenset({"id", "name", "email"}),
            "orders": frozenset({"id", "user_id", "total_amount"}),
        },
    )


def test_allows_readonly_select(policy: AccessPolicy) -> None:
    # JOIN 别名必须解析到对应的白名单表。
    assert validate_readonly_sql(
        "SELECT u.name, o.total_amount FROM users u JOIN orders o ON o.user_id = u.id",
        "sqlite",
        policy,
    ).allowed


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO users (name) VALUES ('x')",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "DROP TABLE users",
        "PRAGMA user_version",
        "SELECT 1; SELECT 2",
        "SELECT * FROM users -- hidden clause",
        "SELECT * FROM sqlite_master",
    ],
)
def test_rejects_unsafe_sql(policy: AccessPolicy, sql: str) -> None:
    # 所有不安全输入都必须在到达 sqlite3 前失败。
    result = validate_readonly_sql(sql, "sqlite", policy)
    assert not result.allowed
    assert result.reason


def test_rejects_unapproved_column(policy: AccessPolicy) -> None:
    # 表名合法不代表该表的所有字段都可访问。
    result = validate_readonly_sql("SELECT email FROM orders", "sqlite", policy)
    assert not result.allowed
    assert result.reason == "column_not_allowed"
