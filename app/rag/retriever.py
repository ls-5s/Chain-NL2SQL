"""Stable schema retrieval contract for P0 and P1 implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from app.schemas.domain import SchemaRetrieval


class SchemaRetrievalError(RuntimeError):
    """检索依赖或索引不可用时的安全边界异常。"""


@dataclass(frozen=True)
class SchemaRetrievalRequest:
    """权限过滤后的单次 Schema 检索请求。"""

    question: str
    database_id: str
    dialect: str
    allowed_tables: frozenset[str] = frozenset()
    allowed_columns: Mapping[str, frozenset[str]] = field(default_factory=dict)


class SchemaRetriever(Protocol):
    """返回固定 Schema 版本，供首次生成和后续修复共同复用。"""

    def retrieve(self, request: SchemaRetrievalRequest) -> SchemaRetrieval: ...
