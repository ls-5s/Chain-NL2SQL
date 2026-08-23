from __future__ import annotations

from app.api.authorization import AccessPolicy
from app.db.result_guard import guard_query_result
from app.graph.state import NL2SQLState
from app.schemas.domain import ErrorCategory, QueryStatus, TraceEvent


def make_result_guard_node(access_policy: AccessPolicy, result_row_limit: int):
    def guard(state: NL2SQLState) -> dict[str, object]:
        if state.get("status") != QueryStatus.SUCCEEDED:
            return {}
        result = guard_query_result(
            sql=state.get("validated_sql") or state.get("generated_sql") or "",
            dialect=state["dialect"],
            result=state.get("query_result"),
            access_policy=access_policy.for_database(state["database_id"]),
            result_row_limit=result_row_limit,
        )
        if not result.allowed:
            return {
                "status": QueryStatus.BLOCKED,
                "query_result": None,
                "error_category": ErrorCategory.PERMISSION_ERROR,
                "safe_error": "The query result could not be verified against the read-only security policy.",
                "answer_source": "deterministic_fallback",
                "trace": state.get("trace", [])
                + [
                    TraceEvent(
                        node="result_guard",
                        iteration=state["iteration"],
                        error_category=ErrorCategory.PERMISSION_ERROR,
                    )
                ],
            }
        return {
            "query_result": result.result,
            "trace": state.get("trace", [])
            + [TraceEvent(node="result_guard", iteration=state["iteration"])],
        }

    return guard
