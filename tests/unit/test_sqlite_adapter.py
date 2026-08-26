from __future__ import annotations

import time
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("sqlglot")

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutionError
from app.db.sqlite_adapter import SQLiteAdapter
from app.demo import DEMO_MASKED_COLUMNS, DEMO_TABLES
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
        allowed_tables=DEMO_TABLES,
        allowed_columns={},
        masked_columns=DEMO_MASKED_COLUMNS,
    )


def test_inspects_schema_and_version(demo_db: Path) -> None:
    # 重复读取时 Schema 检索结果必须保持确定性。
    adapter = SQLiteAdapter("demo", str(demo_db))
    retrieval = adapter.inspect_schema("demo")
    assert {document.table_name for document in retrieval.documents} == DEMO_TABLES
    assert len(retrieval.documents) == 30
    users = next(document for document in retrieval.documents if document.table_name == "用户")
    assert "PRIMARY KEY 编号" in users.content
    assert "邮箱" in users.column_names
    assert retrieval.schema_version == adapter.inspect_schema("demo").schema_version


def test_schema_version_changes_after_schema_change(demo_db: Path) -> None:
    # 结构变化必须使检索版本指纹失效。
    adapter = SQLiteAdapter("demo", str(demo_db))
    before = adapter.inspect_schema("demo").schema_version
    connection = sqlite3.connect(demo_db)
    try:
        connection.execute('ALTER TABLE "用户" ADD COLUMN "测试会员等级" TEXT')
        connection.commit()
    finally:
        connection.close()
    assert adapter.inspect_schema("demo").schema_version != before


def test_executes_with_masking_and_truncation(demo_db: Path, policy: AccessPolicy) -> None:
    # 适配器必须同时完成敏感数据脱敏和行数限制。
    adapter = SQLiteAdapter("demo", str(demo_db), result_row_limit=1)
    result = adapter.execute_readonly(
        'SELECT "邮箱", "用户名称" FROM "用户" ORDER BY "编号"',
        time.monotonic() + 5,
        policy,
    )
    assert result.rows == [["***", "用户0001"]]
    assert result.row_count == 1
    assert result.truncated is True


def test_result_guard_masks_sensitive_alias_after_execution(demo_db: Path, policy: AccessPolicy) -> None:
    adapter = SQLiteAdapter("demo", str(demo_db))
    result = adapter.execute_readonly(
        'SELECT "邮箱" AS "联系方式" FROM "用户" ORDER BY "编号"',
        time.monotonic() + 5,
        policy,
    )
    from app.db.result_guard import guard_query_result

    guarded = guard_query_result(
        sql='SELECT "邮箱" AS "联系方式" FROM "用户" ORDER BY "编号"',
        dialect="sqlite",
        result=result,
        access_policy=policy,
        result_row_limit=100,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert all(row == ["***"] for row in guarded.result.rows)


def test_binds_parameters_without_string_interpolation(
    demo_db: Path, policy: AccessPolicy
) -> None:
    # 参数与 SQL 文本分离传递，避免字符串插值。
    adapter = SQLiteAdapter("demo", str(demo_db))
    result = adapter.execute_readonly(
        'SELECT "用户名称" FROM "用户" WHERE "编号" = ?',
        time.monotonic() + 5,
        policy,
        parameters=(2,),
    )
    assert result.rows == [["用户0002"]]


def test_binds_server_authorized_named_parameters(demo_db: Path, policy: AccessPolicy) -> None:
    adapter = SQLiteAdapter("demo", str(demo_db))
    result = adapter.execute_readonly(
        'SELECT "用户名称" FROM "用户" WHERE "编号" = :selected_user_id',
        time.monotonic() + 5,
        policy,
        parameters={"selected_user_id": 2},
    )
    assert result.rows == [["用户0002"]]


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
