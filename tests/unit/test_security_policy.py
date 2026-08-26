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
        allowed_tables=frozenset({"用户", "订单"}),
        allowed_columns={
            "用户": frozenset({"编号", "用户名称", "邮箱"}),
            "订单": frozenset({"编号", "用户编号", "实付金额"}),
        },
    )


def test_allows_readonly_select(policy: AccessPolicy) -> None:
    # JOIN 别名必须解析到对应的白名单表。
    assert validate_readonly_sql(
        'SELECT u."用户名称", o."实付金额" FROM "用户" AS u JOIN "订单" AS o ON o."用户编号" = u."编号"',
        "sqlite",
        policy,
    ).allowed


@pytest.mark.parametrize(
    "sql",
    [
        'INSERT INTO "用户" ("用户名称") VALUES (\'x\')',
        'UPDATE "用户" SET "用户名称" = \'x\'',
        'DELETE FROM "用户"',
        'DROP TABLE "用户"',
        "PRAGMA user_version",
        "SELECT 1; SELECT 2",
        'SELECT * FROM "用户" -- hidden clause',
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
    result = validate_readonly_sql('SELECT "邮箱" FROM "订单"', "sqlite", policy)
    assert not result.allowed
    assert result.reason == "column_not_allowed"


def test_rejects_projection_wildcard_with_field_policy(policy: AccessPolicy) -> None:
    result = validate_readonly_sql('SELECT * FROM "用户"', "sqlite", policy)
    assert not result.allowed
    assert result.reason == "column_not_allowed"


def test_allows_count_wildcard_with_field_policy(policy: AccessPolicy) -> None:
    result = validate_readonly_sql('SELECT COUNT(*) FROM "用户"', "sqlite", policy)
    assert result.allowed


def test_empty_table_allowlist_denies_all_tables() -> None:
    policy = AccessPolicy(allowed_database_ids=frozenset({"mysql-db"}))

    result = validate_readonly_sql('SELECT 1 FROM "用户"', "mysql", policy)

    assert not result.allowed
    assert result.reason == "table_not_allowed"


def test_rejects_legacy_english_demo_identifiers(policy: AccessPolicy) -> None:
    result = validate_readonly_sql('SELECT "id" FROM "users"', "sqlite", policy)

    assert not result.allowed
    assert result.reason == "table_not_allowed"


def test_allows_authorized_chinese_named_parameter(policy: AccessPolicy) -> None:
    result = validate_readonly_sql(
        'SELECT "编号" FROM "用户" WHERE "编号" = :selected_用户_编号',
        "sqlite",
        policy,
        allowed_parameters={"selected_用户_编号"},
    )

    assert result.allowed
