"""Persistent database registrations and table-level Agent permissions."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config.settings import Settings


@dataclass(frozen=True)
class DatabaseRegistration:
    id: str
    name: str
    dialect: str
    config: dict[str, Any]
    enabled: bool
    created_at: str
    updated_at: str


class DatabaseRegistry:
    """Stores non-secret connection metadata and explicit table permissions."""

    def __init__(self, path: str | Path, settings: Settings) -> None:
        self.path = Path(path).expanduser()
        self.settings = settings
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS database_registry (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    dialect TEXT NOT NULL CHECK(dialect IN ('sqlite', 'mysql')),
                    config_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS database_table_permissions (
                    database_id TEXT NOT NULL REFERENCES database_registry(id) ON DELETE CASCADE,
                    table_name TEXT NOT NULL,
                    agent_access INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (database_id, table_name)
                )
                """
            )
            existing = connection.execute(
                "SELECT id FROM database_registry WHERE id = 'demo'"
            ).fetchone()
            if existing is None:
                now = _now()
                connection.execute(
                    "INSERT INTO database_registry(id, name, dialect, config_json, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                    (
                        "demo",
                        "演示数据库",
                        "sqlite",
                        json.dumps({"path": self.settings.demo_database_path}, ensure_ascii=False),
                        now,
                        now,
                    ),
                )
                for table in ("users", "products", "orders", "order_items"):
                    connection.execute(
                        "INSERT INTO database_table_permissions(database_id, table_name, agent_access, updated_at) VALUES ('demo', ?, 1, ?)",
                        (table, now),
                    )
            self._normalize_enabled(connection)

    @staticmethod
    def _normalize_enabled(connection: sqlite3.Connection) -> None:
        """Keep legacy registries with multiple enabled rows in a single-active state."""
        rows = connection.execute(
            "SELECT id FROM database_registry WHERE enabled = 1 ORDER BY updated_at DESC, id"
        ).fetchall()
        if len(rows) <= 1:
            return
        connection.execute("UPDATE database_registry SET enabled = 0 WHERE enabled = 1")
        connection.execute("UPDATE database_registry SET enabled = 1 WHERE id = ?", (rows[0]["id"],))

    def list(self, *, enabled_only: bool = False) -> list[DatabaseRegistration]:
        with self._connection() as connection:
            query = "SELECT * FROM database_registry"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY name COLLATE NOCASE, id"
            return [_record(row) for row in connection.execute(query).fetchall()]

    def get(self, database_id: str) -> DatabaseRegistration | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM database_registry WHERE id = ?", (database_id,)).fetchone()
        return _record(row) if row else None

    def create(self, *, name: str, dialect: str, config: Mapping[str, Any]) -> DatabaseRegistration:
        database_id = _slug(name)
        now = _now()
        with self._connection() as connection:
            if connection.execute("SELECT 1 FROM database_registry WHERE id = ?", (database_id,)).fetchone():
                raise ValueError("数据库标识已存在，请更换名称。")
            connection.execute("UPDATE database_registry SET enabled = 0 WHERE enabled = 1")
            connection.execute(
                "INSERT INTO database_registry(id, name, dialect, config_json, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                (database_id, name.strip(), dialect, json.dumps(dict(config), ensure_ascii=False), now, now),
            )
        return self.get(database_id)  # type: ignore[return-value]

    def update(self, database_id: str, *, name: str | None = None, config: Mapping[str, Any] | None = None, enabled: bool | None = None) -> DatabaseRegistration:
        current = self.get(database_id)
        if current is None:
            raise KeyError(database_id)
        now = _now()
        with self._connection() as connection:
            next_enabled = current.enabled if enabled is None else enabled
            if enabled is False and current.enabled:
                active_count = connection.execute(
                    "SELECT COUNT(*) FROM database_registry WHERE enabled = 1"
                ).fetchone()[0]
                if active_count <= 1:
                    raise ValueError("至少需要保留一个启用的数据库。")
            if next_enabled:
                connection.execute(
                    "UPDATE database_registry SET enabled = 0, updated_at = ? WHERE id != ? AND enabled = 1",
                    (now, database_id),
                )
            connection.execute(
                "UPDATE database_registry SET name = ?, config_json = ?, enabled = ?, updated_at = ? WHERE id = ?",
                (
                    name.strip() if name else current.name,
                    json.dumps(dict(config), ensure_ascii=False) if config is not None else json.dumps(current.config, ensure_ascii=False),
                    int(next_enabled),
                    now,
                    database_id,
                ),
            )
        return self.get(database_id)  # type: ignore[return-value]

    def delete(self, database_id: str) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM database_registry WHERE id = ?", (database_id,))

    def set_table_access(self, database_id: str, table_name: str, enabled: bool) -> None:
        now = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO database_table_permissions(database_id, table_name, agent_access, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(database_id, table_name) DO UPDATE SET agent_access = excluded.agent_access, updated_at = excluded.updated_at
                """,
                (database_id, table_name, int(enabled), now),
            )

    def sync_tables(self, database_id: str, tables: list[str]) -> None:
        now = _now()
        with self._connection() as connection:
            for table in tables:
                connection.execute(
                    "INSERT OR IGNORE INTO database_table_permissions(database_id, table_name, agent_access, updated_at) VALUES (?, ?, 0, ?)",
                    (database_id, table, now),
                )
            if tables:
                placeholders = ",".join("?" for _ in tables)
                connection.execute(
                    f"DELETE FROM database_table_permissions WHERE database_id = ? AND table_name NOT IN ({placeholders})",
                    (database_id, *tables),
                )

    def table_permissions(self, database_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT table_name, agent_access, updated_at FROM database_table_permissions WHERE database_id = ? ORDER BY table_name COLLATE NOCASE",
                (database_id,),
            ).fetchall()
        return [
            {"table_name": row["table_name"], "agent_access": bool(row["agent_access"]), "updated_at": row["updated_at"]}
            for row in rows
        ]

    def allowed_tables(self, database_id: str) -> frozenset[str]:
        return frozenset(item["table_name"] for item in self.table_permissions(database_id) if item["agent_access"])


def _record(row: sqlite3.Row) -> DatabaseRegistration:
    return DatabaseRegistration(
        id=row["id"],
        name=row["name"],
        dialect=row["dialect"],
        config=json.loads(row["config_json"]),
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _slug(value: str) -> str:
    normalized = "-".join(value.strip().lower().split())
    normalized = "".join(char for char in normalized if char.isalnum() or char == "-")
    return normalized[:80] or str(uuid4())


def _now() -> str:
    return datetime.now(UTC).isoformat()
