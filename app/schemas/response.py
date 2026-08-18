"""Stable API response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.domain import ErrorCategory, QueryResult, QueryStatus, TraceEvent


class QueryResponse(BaseModel):
    """查询接口的统一响应，不包含原始异常或未授权 SQL。"""

    request_id: str
    status: QueryStatus
    iteration: int
    error_category: ErrorCategory | None = None
    final_answer: str
    result: QueryResult | None = None
    trace: list[TraceEvent] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """不依赖外部模型和数据库的服务健康状态。"""

    status: str = "ok"
    environment: str


class DatabaseListResponse(BaseModel):
    """服务端允许暴露给当前环境的数据库标识列表。"""

    database_ids: list[str]
