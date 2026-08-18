from __future__ import annotations

import time
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("sqlglot")

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutionError
from app.db.sqlite_adapter import SQLiteAdapter
from scripts.init_demo_db import initialize


ROOT = Path(__file__).parents[2]


@pytest.fixture
def demo_db(tmp_path: Path) -> Path:
    # 每个测试都根据确定性 fixture 创建隔离数据库。
    path = tmp_path / "demo.sqlite"
    initialize(path, ROOT / "data" / "fixtures" / "demo.sql")
    return path


@pytest.fixture
def policy() -> AccessPolicy:
    # 模拟适配器使用的服务端 P0 策略。
    return AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=frozenset({"users", "products", "orders", "order_items"}),
        allowed_columns={
            "users": frozenset({"id", "name", "email", "created_at"}),
            "products": frozenset({"id", "name", "category", "price"}),
            "orders": frozenset({"id", "user_id", "status", "total_amount", "created_at"}),
            "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
        },
        masked_columns=frozenset({"users.email"}),
    )


def test_inspects_schema_and_version(demo_db: Path) -> None:
    # 重复读取时 Schema 检索结果必须保持确定性。
    adapter = SQLiteAdapter("demo", str(demo_db))
    retrieval = adapter.inspect_schema("demo")
    assert [document.table_name for document in retrieval.documents] == [
        "order_items",
        "orders",
        "products",
        "users",
    ]
    users = next(document for document in retrieval.documents if document.table_name == "users")
    assert "PRIMARY KEY id" in users.content
    assert "email" in users.column_names
    assert retrieval.schema_version == adapter.inspect_schema("demo").schema_version


def test_schema_version_changes_after_schema_change(demo_db: Path) -> None:
    # 结构变化必须使检索版本指纹失效。
    adapter = SQLiteAdapter("demo", str(demo_db))
    before = adapter.inspect_schema("demo").schema_version
    connection = sqlite3.connect(demo_db)
    try:
        connection.execute("ALTER TABLE users ADD COLUMN loyalty_tier TEXT")
        connection.commit()
    finally:
        connection.close()
    assert adapter.inspect_schema("demo").schema_version != before


def test_executes_with_masking_and_truncation(demo_db: Path, policy: AccessPolicy) -> None:
    # 适配器必须同时完成敏感数据脱敏和行数限制。
    adapter = SQLiteAdapter("demo", str(demo_db), result_row_limit=1)
    result = adapter.execute_readonly(
        "SELECT email, name FROM users ORDER BY id",
        time.monotonic() + 5,
        policy,
    )
    assert result.rows == [["***", "Alice"]]
    assert result.row_count == 1
    assert result.truncated is True


def test_binds_parameters_without_string_interpolation(
    demo_db: Path, policy: AccessPolicy
) -> None:
    # 参数与 SQL 文本分离传递，避免字符串插值。
    adapter = SQLiteAdapter("demo", str(demo_db))
    result = adapter.execute_readonly(
        "SELECT name FROM users WHERE id = ?",
        time.monotonic() + 5,
        policy,
        parameters=(2,),
    )
    assert result.rows == [["Bob"]]


def test_deadline_is_enforced(demo_db: Path, policy: AccessPolicy) -> None:
    # 过期请求必须在创建连接前被拒绝。
    adapter = SQLiteAdapter("demo", str(demo_db))
    with pytest.raises(DatabaseExecutionError, match="deadline"):
        adapter.execute_readonly("SELECT 1", time.monotonic() - 1, policy)


def test_wrong_database_is_rejected(demo_db: Path, policy: AccessPolicy) -> None:
    # 适配器身份和请求策略必须对数据库 ID 达成一致。
    adapter = SQLiteAdapter("demo", str(demo_db))
    with pytest.raises(DatabaseExecutionError) as error:
        adapter.inspect_schema("other")
    assert error.value.category == "permission_error"
