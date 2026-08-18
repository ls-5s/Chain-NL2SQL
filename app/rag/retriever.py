"""Stable schema retrieval contract for P0 and P1 implementations."""

from __future__ import annotations

from typing import Protocol

from app.schemas.domain import SchemaRetrieval


class SchemaRetriever(Protocol):
    """返回固定 Schema 版本，供首次生成和后续修复共同复用。"""

    def retrieve(self, question: str, database_id: str) -> SchemaRetrieval: ...
