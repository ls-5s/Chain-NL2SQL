"""Database adapter interface."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.api.authorization import AccessPolicy
from app.schemas.domain import QueryResult, SchemaRetrieval


class DatabaseExecutor(Protocol):
    """隔离 SQLite/MySQL 驱动差异的只读数据库接口。"""

    def inspect_schema(self, database_id: str) -> SchemaRetrieval: ...

    def execute_readonly(
        self, sql: str, deadline: datetime, access_policy: AccessPolicy
    ) -> QueryResult: ...

    def close(self) -> None: ...
