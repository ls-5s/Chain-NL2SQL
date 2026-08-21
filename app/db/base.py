"""数据库适配器接口。"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from app.api.authorization import AccessPolicy
from app.schemas.domain import QueryResult, SchemaRetrieval


class DatabaseExecutionError(RuntimeError):
    """数据库驱动异常离开底层时使用的安全、类型化边界。"""

    def __init__(self, category: str, safe_message: str) -> None:
        # 在边界处只保存稳定分类和脱敏后的消息。
        super().__init__(safe_message)
        self.category = category
        self.safe_message = safe_message


class DatabaseExecutor(Protocol):
    """隔离 SQLite/MySQL 驱动差异的只读数据库接口。"""

    def inspect_schema(self, database_id: str) -> SchemaRetrieval: ...

    def get_schema_version(self, database_id: str) -> str: ...

    # deadline 是 time.monotonic() 时间轴上的绝对值，不是墙上时钟时间。
    def execute_readonly(
        self,
        sql: str,
        deadline: float,
        access_policy: AccessPolicy,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
    ) -> QueryResult: ...

    def close(self) -> None: ...
