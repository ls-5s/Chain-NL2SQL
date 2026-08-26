"""LLM review gate for SQL output fields before execution."""

from __future__ import annotations

import json

from app.graph.state import NL2SQLState
from app.llm.client import LLMClient
from app.llm.prompts import build_sql_projection_review_prompt
from app.schemas.domain import QueryStatus, TraceEvent


def make_projection_review_node(llm_client: LLMClient, timeout_seconds: float):
    prompt_template = build_sql_projection_review_prompt()

    def review(state: NL2SQLState) -> dict[str, object]:
        if state["status"] != QueryStatus.RUNNING:
            return {}
        sql = state.get("generated_sql")
        if not sql:
            return _invalid_decision(state, "No SQL was available for projection review.")
        schema_context = "\n\n".join(document.content for document in state.get("schema_context", []))
        try:
            response = llm_client.generate(
                prompt_template.invoke(
                    {
                        "question": state["question"],
                        "schema_context": schema_context,
                        "sql": sql,
                    }
                ),
                timeout_seconds=timeout_seconds,
            )
            decision = json.loads(response.content.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            return _invalid_decision(state, "The SQL projection review did not return a valid decision.")
        except Exception:
            return _invalid_decision(state, "The SQL projection review is unavailable.")
        if not isinstance(decision, dict) or type(decision.get("valid")) is not bool:
            return _invalid_decision(state, "The SQL projection review did not return a valid decision.")
        if decision["valid"]:
            return {
                "projection_review_reason": None,
                "trace": state.get("trace", [])
                + [TraceEvent(node="review_sql_projection", iteration=state["iteration"])],
            }
        reason = decision.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return _invalid_decision(state, "The SQL projection review did not return a valid decision.")
        return {
            "status": QueryStatus.FAILED,
            "error_category": "projection_mismatch",
            "safe_error": "The generated SQL selected fields that were not requested.",
            "projection_review_reason": reason.strip()[:500],
            "trace": state.get("trace", [])
            + [TraceEvent(node="review_sql_projection", iteration=state["iteration"], error_category="projection_mismatch")],
        }

    return review


def _invalid_decision(state: NL2SQLState, message: str) -> dict[str, object]:
    return {
        "status": QueryStatus.FAILED,
        "error_category": "invalid_model_output",
        "safe_error": message,
        "projection_review_reason": None,
        "trace": state.get("trace", [])
        + [TraceEvent(node="review_sql_projection", iteration=state["iteration"], error_category="invalid_model_output")],
    }
