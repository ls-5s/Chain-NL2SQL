"""本地开发环境的访问策略。

P0 不提供远程多用户访问。P1 可替换为基于 API Key 的身份和数据库授权，且不改变路由签名。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.config.settings import Settings
from app.demo import DEMO_MASKED_COLUMNS, DEMO_TABLES


@dataclass(frozen=True)
class AccessPolicy:
    """请求可访问的数据范围；P1 可由 API Key/RBAC 解析后填充。"""

    allowed_database_ids: frozenset[str]
    can_view_debug_sql: bool = False
    allowed_tables: frozenset[str] = frozenset()
    allowed_columns: Mapping[str, frozenset[str]] | None = None
    masked_columns: frozenset[str] = frozenset()
    allowed_tables_by_database: Mapping[str, frozenset[str]] | None = None
    allowed_columns_by_database: Mapping[str, Mapping[str, frozenset[str]]] | None = None
    masked_columns_by_database: Mapping[str, frozenset[str]] | None = None
    # 把所有表名、列名全部统一转小写。
    def __post_init__(self) -> None:
        # 初始化时统一策略名称，便于不区分大小写地比较 SQL 标识符。
        object.__setattr__(self, "allowed_tables", frozenset(table.lower() for table in self.allowed_tables))
        object.__setattr__(self, "masked_columns", frozenset(column.lower() for column in self.masked_columns))
        if self.allowed_columns is None:
            object.__setattr__(self, "allowed_columns", {})
        else:
            object.__setattr__(
                self,
                "allowed_columns",
                {
                    table.lower(): frozenset(column.lower() for column in columns)
                    for table, columns in self.allowed_columns.items()
                },
            )
        object.__setattr__(
            self,
            "allowed_tables_by_database",
            {
                database_id: frozenset(table.lower() for table in tables)
                for database_id, tables in (self.allowed_tables_by_database or {}).items()
            },
        )
        object.__setattr__(
            self,
            "allowed_columns_by_database",
            {
                database_id: {
                    table.lower(): frozenset(column.lower() for column in columns)
                    for table, columns in tables.items()
                }
                for database_id, tables in (self.allowed_columns_by_database or {}).items()
            },
        )
        object.__setattr__(
            self,
            "masked_columns_by_database",
            {
                database_id: frozenset(column.lower() for column in columns)
                for database_id, columns in (self.masked_columns_by_database or {}).items()
            },
        )

    def for_database(self, database_id: str) -> "AccessPolicy":
        """Return the policy scoped to one database, preserving legacy defaults."""

        if self.allowed_tables_by_database:
            tables = self.allowed_tables_by_database.get(database_id, frozenset())
            columns = (self.allowed_columns_by_database or {}).get(database_id, {})
            masked = (self.masked_columns_by_database or {}).get(database_id, frozenset())
        else:
            tables = self.allowed_tables
            columns = self.allowed_columns or {}
            masked = self.masked_columns
        return AccessPolicy(
            allowed_database_ids=frozenset({database_id}) if database_id in self.allowed_database_ids else frozenset(),
            can_view_debug_sql=self.can_view_debug_sql,
            allowed_tables=tables,
            allowed_columns=columns,
            masked_columns=masked,
        )


def local_access_policy(settings: Settings, database_ids: frozenset[str] | None = None) -> AccessPolicy:
    # Database IDs are supplied by the server-side registry. The legacy
    # settings field is intentionally ignored so new registrations are usable.
    # The demo schema is generated locally and all of its public fields are readable.
    return AccessPolicy(
        allowed_database_ids=database_ids or frozenset(),
        allowed_tables=DEMO_TABLES,
        allowed_columns={},
        masked_columns=DEMO_MASKED_COLUMNS,
    )
