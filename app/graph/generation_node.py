from __future__ import annotations

from app.graph.state import NL2SQLState
from app.llm.client import LLMClient
from app.llm.output_parser import extract_sql
from app.llm.prompts import build_sql_generation_prompt


def make_generation_node(llm_client: LLMClient, timeout_seconds: float):
    prompt_template = build_sql_generation_prompt()

    def generate(state: NL2SQLState) -> dict[str, object]:
        if state["status"] != "running":
            return {}
        schema_context = "\n\n".join(document.content for document in state.get("schema_context", []))
        response = llm_client.generate(
            prompt_template.invoke({
                "dialect": state["dialect"],
                "schema_context": schema_context,
                "question": state["question"],
            }),
            timeout_seconds=timeout_seconds,
        )
        sql = extract_sql(response.content)
        if not sql:
            return {"status": "failed", "error_category": "invalid_model_output", "safe_error": "The model did not return valid read-only SQL."}
        return {"generated_sql": sql, "iteration": state["iteration"] + 1}

    return generate
