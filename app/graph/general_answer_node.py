"""General LLM response path that never reads database state."""

from __future__ import annotations

from app.graph.state import NL2SQLState
from app.llm.client import LLMClient
from app.llm.prompts import build_general_answer_prompt
from app.schemas.domain import QueryStatus


def make_general_answer_node(llm_client: LLMClient, timeout_seconds: float):
    prompt_template = build_general_answer_prompt()

    def answer(state: NL2SQLState) -> dict[str, object]:
        response = llm_client.generate(
            prompt_template.invoke({"question": state["question"]}),
            timeout_seconds=timeout_seconds,
        )
        return {"status": QueryStatus.SUCCEEDED, "final_answer": response.content.strip()}

    return answer
