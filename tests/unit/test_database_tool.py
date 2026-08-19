from __future__ import annotations

from pathlib import Path

from app.api.authorization import AccessPolicy
from app.db.sqlite_adapter import SQLiteAdapter
from app.db.tools import create_query_database_tool


ROOT = Path(__file__).resolve().parents[2]


def policy() -> AccessPolicy:
    return AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=frozenset({"users", "products", "orders", "order_items"}),
        allowed_columns={
            "users": frozenset({"id", "name", "email", "created_at"}),
            "products": frozenset({"id", "name", "category", "price"}),
            "orders": frozenset({"id", "user_id", "status", "total_amount", "created_at"}),
            "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
        },
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
        {"sql": "SELECT name FROM users WHERE id = ?", "parameters": [2]}
    )

    assert result == {
        "ok": True,
        "result": {
            "columns": ["name"],
            "rows": [["Bob"]],
            "row_count": 1,
            "truncated": False,
        },
    }


def test_query_database_tool_returns_safe_error_for_unsafe_sql() -> None:
    result = make_tool().invoke({"sql": "DELETE FROM users", "parameters": []})

    assert result["ok"] is False
    assert result["error_category"] == "unsafe_sql"
    assert "DELETE" not in result["message"]
