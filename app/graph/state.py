"""Typed graph state and safe initialization."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from app.schemas.domain import AnswerSource, ErrorCategory, KnowledgeHit, QueryIntent, QueryResult, QueryStatus, SchemaDocument, TraceEvent


class NL2SQLState(TypedDict):
    """LangGraph 节点间共享的状态；必填字段由初始状态一次性创建。"""

    request_id: str
    question: str
    database_id: str | None
    dialect: str
    iteration: int
    max_iterations: int
    trace: list[TraceEvent]
    status: QueryStatus
    conversation_context: NotRequired[str]
    conversation_data_context: NotRequired[dict[str, object]]
    bound_parameters: NotRequired[dict[str, object]]
    knowledge_policy: NotRequired[str]
    clarification_fields: NotRequired[list[str]]
    required_actions: NotRequired[list[str]]
    pending_clarification: NotRequired[dict[str, object]]
    database_runtime: NotRequired[object]
    schema_retriever_runtime: NotRequired[object]
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
    projection_review_reason: NotRequired[str | None]
    validated_sql: NotRequired[str]
    query_result: NotRequired[QueryResult | None]
    raw_error: NotRequired[str | None]
    safe_error: NotRequired[str | None]
    error_category: NotRequired[ErrorCategory | None]
    final_answer: NotRequired[str | None]
    answer_source: NotRequired[AnswerSource | str | None]
    knowledge_hits: NotRequired[list[KnowledgeHit]]
    knowledge_context: NotRequired[str]
    knowledge_retrieval_error: NotRequired[str | None]


def create_initial_state(
    *,
    request_id: str,
    question: str,
    database_id: str | None = None,
    dialect: str = "",
    max_iterations: int,
    conversation_context: str = "",
    conversation_data_context: dict[str, object] | None = None,
    bound_parameters: dict[str, object] | None = None,
    knowledge_policy: str = "none",
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
        "conversation_data_context": conversation_data_context or {"candidates": []},
        "bound_parameters": bound_parameters or {},
        "knowledge_policy": knowledge_policy,
    }
