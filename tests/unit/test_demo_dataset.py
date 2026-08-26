from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from app.demo import DEMO_TABLES
from app.api.authorization import AccessPolicy
from app.db.security_policy import validate_readonly_sql
from app.rag.index_manager import SchemaIndexManager
from app.rag.retriever import SchemaRetrievalRequest
from app.db.sqlite_adapter import SQLiteAdapter
from scripts.build_demo_schema_rag import build
from scripts.init_demo_db import initialize


ROOT = Path(__file__).resolve().parents[2]


def test_demo_initializer_creates_thirty_consistent_data_tables(tmp_path: Path) -> None:
    database = tmp_path / "demo.sqlite"
    initialize(database, ROOT / "data" / "fixtures" / "demo.sql")
    connection = sqlite3.connect(database)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")}
        counts = {table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in DEMO_TABLES}
        assert tables == DEMO_TABLES
        assert min(counts.values()) == 1000
        assert sum(counts.values()) == 30000
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute('SELECT "用户名称" FROM "用户" WHERE "编号" = 1').fetchone()[0] == "用户0001"
        assert connection.execute('SELECT "实付金额" FROM "订单" WHERE "编号" = 1').fetchone()[0] > 0
        index_names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
        assert {"索引_订单_用户时间", "索引_库存_商品仓库", "索引_物流_订单"} <= index_names
        assert len(connection.execute('PRAGMA table_info("订单")').fetchall()) == 20
        assert len(connection.execute('PRAGMA table_info("商品")').fetchall()) == 18
    finally:
        connection.close()


def test_demo_initializer_is_repeatable_and_schema_rag_indexes_all_tables(tmp_path: Path) -> None:
    first = tmp_path / "first.sqlite"
    second = tmp_path / "second.sqlite"
    initialize(first, ROOT / "data" / "fixtures" / "demo.sql")
    initialize(second, ROOT / "data" / "fixtures" / "demo.sql")
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(second.read_bytes()).hexdigest()

    payload = build(first, tmp_path / "schema")
    assert payload["indexed_table_count"] == 30
    adapter = SQLiteAdapter("demo", str(first))
    manager = SchemaIndexManager(adapter.inspect_schema, root=tmp_path / "schema-query", mode="bm25", top_k=5)
    result = manager.retrieve(SchemaRetrievalRequest("查询仓库库存和物流", "demo", "sqlite", DEMO_TABLES, {}))
    assert {"库存", "物流单"} & {document.table_name for document in result.documents}


def test_demo_permissions_reject_disabled_and_english_identifiers(tmp_path: Path) -> None:
    database = tmp_path / "demo.sqlite"
    initialize(database, ROOT / "data" / "fixtures" / "demo.sql")
    adapter = SQLiteAdapter("demo", str(database))
    allowed_tables = DEMO_TABLES - {"订单"}
    manager = SchemaIndexManager(adapter.inspect_schema, root=tmp_path / "schema-permissions", mode="bm25", top_k=30)
    retrieval = manager.retrieve(SchemaRetrievalRequest("查询订单", "demo", "sqlite", allowed_tables, {}))
    assert "订单" not in {document.table_name for document in retrieval.documents}

    policy = AccessPolicy(allowed_database_ids=frozenset({"demo"}), allowed_tables=allowed_tables)
    assert not validate_readonly_sql('SELECT "编号" FROM "订单"', "sqlite", policy).allowed
    assert not validate_readonly_sql('SELECT "id" FROM "users"', "sqlite", policy).allowed
