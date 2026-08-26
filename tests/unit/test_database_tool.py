from __future__ import annotations

from pathlib import Path

from app.api.authorization import AccessPolicy
from app.db.sqlite_adapter import SQLiteAdapter
from app.demo import DEMO_TABLES
from app.db.tools import create_query_database_tool


ROOT = Path(__file__).resolve().parents[2]


def policy() -> AccessPolicy:
    return AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=DEMO_TABLES,
        allowed_columns={},
    )


def make_tool():
    adapter = SQLiteAdapter("demo", str(ROOT / "data" / "demo.sqlite"))
    return create_query_database_tool(
        database_executor=adapter,
        access_policy=policy(),
        timeout_seconds=5,
    )


def test_query_database_tool_executes_parameterized_readonly_sql() -> None:
    result = make_tool().invoke(
        {"sql": 'SELECT "用户名称" FROM "用户" WHERE "编号" = ?', "parameters": [2]}
    )

    assert result == {
        "ok": True,
        "result": {
            "columns": ["用户名称"],
            "rows": [["用户0002"]],
            "row_count": 1,
            "truncated": False,
        },
    }


def test_query_database_tool_returns_safe_error_for_unsafe_sql() -> None:
    result = make_tool().invoke({"sql": 'DELETE FROM "用户"', "parameters": []})

    assert result["ok"] is False
    assert result["error_category"] == "unsafe_sql"
    assert "DELETE" not in result["message"]
