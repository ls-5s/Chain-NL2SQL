from __future__ import annotations

import json

from app.graph.state import NL2SQLState
from app.llm.client import LLMClient
from app.llm.prompts import build_grounded_answer_prompt
from app.schemas.domain import AnswerSource, QueryStatus


def make_grounded_answer_node(llm_client: LLMClient, timeout_seconds: float):
    prompt = build_grounded_answer_prompt()

    def answer(state: NL2SQLState) -> dict[str, object]:
        hits = state.get("knowledge_hits", [])
        if not hits or any(not hit.document_id or not hit.excerpt.strip() for hit in hits):
            return {"status": QueryStatus.NO_GROUNDED_ANSWER, "final_answer": "NO_GROUNDED_ANSWER：没有找到可验证的授权资料。", "answer_source": AnswerSource.DETERMINISTIC_FALLBACK}
        evidence = [{"document_id": hit.document_id, "title": hit.title, "excerpt": hit.excerpt} for hit in hits]
        try:
            answer_text = llm_client.generate(
                prompt.invoke({"question": state["question"], "evidence_json": json.dumps(evidence, ensure_ascii=False)}),
                timeout_seconds=timeout_seconds,
            ).content.strip()
        except Exception:
            answer_text = ""
        if not answer_text:
            answer_text = "；".join(f"[{hit.document_id}] {hit.excerpt}" for hit in hits)
        if not any(hit.document_id in answer_text for hit in hits):
            return {
                "status": QueryStatus.NO_GROUNDED_ANSWER,
                "final_answer": "NO_GROUNDED_ANSWER：模型回答缺少可验证引用。",
                "answer_source": AnswerSource.DETERMINISTIC_FALLBACK,
            }
        return {"status": QueryStatus.SUCCEEDED, "final_answer": answer_text, "answer_source": AnswerSource.GENERAL_LLM}

    return answer
