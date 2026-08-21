"""Typed graph state and safe initialization."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from app.schemas.domain import ErrorCategory, QueryIntent, QueryResult, QueryStatus, SchemaDocument, TraceEvent


class NL2SQLState(TypedDict):
    """LangGraph 节点间共享的状态；必填字段由初始状态一次性创建。"""

    request_id: str
    question: str
    database_id: str
    dialect: str
    iteration: int
    max_iterations: int
    trace: list[TraceEvent]
    status: QueryStatus
    conversation_context: NotRequired[str]
    bound_parameters: NotRequired[dict[str, object]]
    # 以下字段由对应节点按需追加，路由前必须检查其是否存在。
    schema_version: NotRequired[str]
    intent: NotRequired[QueryIntent]
    intent_confidence: NotRequired[float]
    intent_reason: NotRequired[str]
    intent_source: NotRequired[str]
    intent_classification_valid: NotRequired[bool]
    schema_context: NotRequired[list[SchemaDocument]]
    retrieval_mode: NotRequired[str]
    retrieval_scores: NotRequired[dict[str, float]]
    retrieved_tables: NotRequired[list[str]]
    generated_sql: NotRequired[str]
    validated_sql: NotRequired[str]
    query_result: NotRequired[QueryResult | None]
    raw_error: NotRequired[str | None]
    safe_error: NotRequired[str | None]
    error_category: NotRequired[ErrorCategory | None]
    final_answer: NotRequired[str | None]


def create_initial_state(
    *,
    request_id: str,
    question: str,
    database_id: str,
    dialect: str,
    max_iterations: int,
    conversation_context: str = "",
    bound_parameters: dict[str, object] | None = None,
) -> NL2SQLState:
    # iteration=0 表示首次 SQL 尝试；后续修复节点才会递增该计数。
    return {
        "request_id": request_id,
        "question": question,
        "database_id": database_id,
        "dialect": dialect,
        "iteration": 0,
        "max_iterations": max_iterations,
        "trace": [],
        "status": QueryStatus.RUNNING,
        "conversation_context": conversation_context,
        "bound_parameters": bound_parameters or {},
    }
