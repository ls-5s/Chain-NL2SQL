"""General LLM response path with optional untrusted knowledge context."""

from __future__ import annotations

from app.graph.state import NL2SQLState
from app.llm.client import LLMClient
from app.llm.prompts import build_general_answer_prompt
from app.schemas.domain import AnswerSource, QueryStatus


def make_general_answer_node(llm_client: LLMClient, timeout_seconds: float):
    prompt_template = build_general_answer_prompt()

    def answer(state: NL2SQLState) -> dict[str, object]:
        if state.get("knowledge_policy") == "required":
            return {
                "status": QueryStatus.NO_GROUNDED_ANSWER,
                "final_answer": "NO_GROUNDED_ANSWER：当前没有可验证的内部资料，无法提供可靠回答。",
                "answer_source": AnswerSource.DETERMINISTIC_FALLBACK,
            }
        response = llm_client.generate(
            prompt_template.invoke({
                "question": state["question"],
                "conversation_context": state.get("conversation_context", ""),
            }),
            timeout_seconds=timeout_seconds,
        )
        answer = response.content.strip()
        if not answer:
            return {
                "status": QueryStatus.FAILED,
                "error_category": "invalid_model_output",
                "safe_error": "通用回答模型未返回有效内容。",
                "answer_source": AnswerSource.DETERMINISTIC_FALLBACK,
            }
        return {
            "status": QueryStatus.SUCCEEDED,
            "final_answer": answer,
            "answer_source": AnswerSource.GENERAL_LLM,
        }

    return answer
