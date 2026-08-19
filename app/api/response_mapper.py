"""Convert internal graph state to the public response model."""

from __future__ import annotations

from typing import Any

from app.schemas.domain import ErrorCategory, QueryIntent, QueryStatus
from app.schemas.response import QueryResponse


def map_query_state(state: dict[str, Any]) -> QueryResponse:
    status = state.get("status", QueryStatus.FAILED)
    if not isinstance(status, QueryStatus):
        status = QueryStatus(status)
    category = state.get("error_category")
    if category is not None and not isinstance(category, ErrorCategory):
        category = ErrorCategory(category)
    intent = state.get("intent", QueryIntent.CLARIFICATION)
    if not isinstance(intent, QueryIntent):
        intent = QueryIntent(intent)
    return QueryResponse(
        request_id=state["request_id"],
        intent=intent,
        intent_confidence=state.get("intent_confidence"),
        intent_reason=state.get("intent_reason"),
        intent_source=state.get("intent_source"),
        status=status,
        iteration=state.get("iteration", 0),
        error_category=category,
        final_answer=state.get("final_answer") or "查询未完成。",
        result=state.get("query_result"),
        generated_sql=state.get("generated_sql"),
        trace=state.get("trace", []),
    )
