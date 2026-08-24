"""Convert internal graph state to the public response model."""

from __future__ import annotations

from typing import Any

from app.schemas.domain import AnswerSource, ErrorCategory, QueryIntent, QueryStatus
from app.schemas.response import QueryResponse


def map_query_state(state: dict[str, Any]) -> QueryResponse:
    status = state.get("status", QueryStatus.FAILED)
    if not isinstance(status, QueryStatus):
        status = QueryStatus(status)
    category = state.get("error_category")
    if category is not None and not isinstance(category, ErrorCategory):
        category = ErrorCategory(category)
    intent_value = state.get("intent", QueryIntent.GENERAL_CHAT)
    if isinstance(intent_value, QueryIntent):
        intent = intent_value
    else:
        # Unknown persisted turns remain renderable as general chat.
        try:
            intent = QueryIntent(intent_value)
        except ValueError:
            intent = QueryIntent.GENERAL_CHAT
    # Summary requests need the full guarded result internally, but returning
    # every article body to the browser duplicates the answer and overwhelms
    # the conversation. Keep only the generated summary in the public payload.
    display_result = None if _is_summary_request(state.get("question", "")) else state.get("query_result")
    return QueryResponse(
        request_id=state["request_id"],
        intent=intent,
        intent_confidence=state.get("intent_confidence"),
        intent_reason=state.get("intent_reason"),
        intent_source=state.get("intent_source"),
        answer_source=_answer_source(state.get("answer_source")),
        status=status,
        iteration=state.get("iteration", 0),
        error_category=category,
        final_answer=state.get("final_answer") or "查询未完成。",
        result=display_result,
        generated_sql=state.get("generated_sql"),
        trace=state.get("trace", []),
        knowledge_hits=state.get("knowledge_hits", []),
        clarification_fields=state.get("clarification_fields", []),
        required_actions=state.get("required_actions", []),
    )


def _is_summary_request(question: str) -> bool:
    return any(marker in question for marker in ("总结", "摘要", "概括", "分别介绍", "每篇", "各篇"))


def _answer_source(value: Any) -> AnswerSource | None:
    if value is None:
        return None
    if isinstance(value, AnswerSource):
        return value
    try:
        return AnswerSource(value)
    except ValueError:
        return None
