"""Stable API response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.domain import ErrorCategory, QueryIntent, QueryResult, QueryStatus, TraceEvent


class QueryResponse(BaseModel):
    """查询接口的统一响应，不包含原始异常或未授权 SQL。"""

    request_id: str
    intent: QueryIntent
    intent_confidence: float | None = None
    intent_reason: str | None = None
    intent_source: str | None = None
    status: QueryStatus
    iteration: int
    error_category: ErrorCategory | None = None
    final_answer: str
    result: QueryResult | None = None
    generated_sql: str | None = None
    trace: list[TraceEvent] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """不依赖外部模型和数据库的服务健康状态。"""

    status: str = "ok"
    environment: str


class DatabaseListResponse(BaseModel):
    """服务端允许暴露给当前环境的数据库标识列表。"""

    database_ids: list[str]


class SessionResponse(BaseModel):
    authenticated: bool
    username: str | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    database_id: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationMessage(BaseModel):
    id: str
    turn_id: str
    role: str
    content: str
    status: str
    response: QueryResponse | None = None
    progress: list[dict[str, object]] = Field(default_factory=list)
    created_at: str


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage] = Field(default_factory=list)


class ResultReferenceResponse(BaseModel):
    id: str
    label: str
