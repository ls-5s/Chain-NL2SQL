"""Repair retry node that reuses the first retrieval context."""

from __future__ import annotations

from app.graph.state import NL2SQLState
from app.llm.client import LLMClient
from app.llm.output_parser import extract_sql
from app.llm.prompts import build_sql_repair_prompt
from app.schemas.domain import TraceEvent


REPAIRABLE_ERRORS = frozenset({
    "syntax_error",
    "unknown_column",
    "unknown_table",
    "join_error",
    "aggregation_error",
})


def make_repair_node(llm_client: LLMClient, timeout_seconds: float):
    prompt_template = build_sql_repair_prompt()

    def repair(state: NL2SQLState) -> dict[str, object]:
        if state["status"] != "failed":
            return {}
        category = state.get("error_category")
        category_value = category.value if hasattr(category, "value") else category
        if category_value not in REPAIRABLE_ERRORS or state["iteration"] >= state["max_iterations"]:
            return {}
        schema_context = "\n\n".join(document.content for document in state.get("schema_context", []))
        response = llm_client.generate(
            prompt_template.invoke(
                {
                    "dialect": state["dialect"],
                    "schema_context": schema_context,
                    "question": state["question"],
                    "conversation_context": state.get("conversation_context", ""),
                    "failed_sql": state.get("generated_sql", ""),
                    "error_message": state.get("safe_error", ""),
                }
            ),
            timeout_seconds=timeout_seconds,
        )
        sql = extract_sql(response.content)
        if not sql:
            return {
                "status": "failed",
                "error_category": "invalid_model_output",
                "safe_error": "The repair model did not return valid read-only SQL.",
            }
        return {
            "status": "running",
            "generated_sql": sql,
            "validated_sql": None,
            "query_result": None,
            "iteration": state["iteration"] + 1,
            "error_category": None,
            "safe_error": None,
            "trace": state.get("trace", [])
            + [TraceEvent(node="repair_sql", iteration=state["iteration"], error_category=category_value)],
        }

    return repair
