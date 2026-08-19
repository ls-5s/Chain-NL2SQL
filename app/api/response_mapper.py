"""Convert internal graph state to the public response model."""

from __future__ import annotations

from typing import Any

from app.schemas.domain import ErrorCategory, QueryStatus
from app.schemas.response import QueryResponse


def map_query_state(state: dict[str, Any]) -> QueryResponse:
    status = state.get("status", QueryStatus.FAILED)
    if not isinstance(status, QueryStatus):
        status = QueryStatus(status)
    category = state.get("error_category")
    if category is not None and not isinstance(category, ErrorCategory):
        category = ErrorCategory(category)
    return QueryResponse(
        request_id=state["request_id"],
        status=status,
        iteration=state.get("iteration", 0),
        error_category=category,
        final_answer=state.get("final_answer") or "查询未完成。",
        result=state.get("query_result"),
        generated_sql=state.get("generated_sql"),
        trace=state.get("trace", []),
    )
