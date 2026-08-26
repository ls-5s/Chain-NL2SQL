"""LLM intent gate that runs before Schema retrieval."""

from __future__ import annotations

import json
from typing import Any

from app.graph.state import NL2SQLState
from app.graph.intent_rules import classify_by_rules
from app.llm.client import LLMClient
from app.llm.prompts import build_intent_classification_prompt
from app.schemas.domain import QueryIntent


def make_intent_gate_node(llm_client: LLMClient, timeout_seconds: float, confidence_threshold: float = 0.75):
    prompt_template = build_intent_classification_prompt()

    def classify(state: NL2SQLState) -> dict[str, object]:
        # The API may preflight this gate before a database runtime exists.
        if state.get("intent") is not None:
            return {"intent": state["intent"]}
        rule_decision = classify_by_rules(state["question"])
        if rule_decision is not None and _requires_knowledge_retrieval(state["question"]):
            return _rule_result(state["question"], rule_decision)
        if rule_decision is not None and rule_decision.intent == QueryIntent.DATA_QUERY:
            return _rule_result(state["question"], rule_decision)
        if rule_decision is not None and not _has_data_candidates(state.get("conversation_data_context")):
            return _rule_result(state["question"], rule_decision)
        response = llm_client.generate(
            prompt_template.invoke(
                {
                    "question": state["question"],
                    "conversation_context": state.get("conversation_context", ""),
                    "conversation_data_context": json.dumps(
                        state.get("conversation_data_context", {"candidates": []}),
                        ensure_ascii=False,
                        default=str,
                    ),
                }
            ),
            timeout_seconds=timeout_seconds,
        )
        parsed = _parse_intent(response.content)
        if parsed is None or parsed["confidence"] < confidence_threshold:
            return _llm_result(
                state["question"],
                QueryIntent.CLARIFY,
                parsed["confidence"] if parsed else 0.0,
                "LLM 分类置信度不足或输出格式无效",
                False,
            )
        return _llm_result(
            state["question"], parsed["intent"], parsed["confidence"], parsed["reason"], True
        )

    return classify


def _rule_result(question: str, decision: Any) -> dict[str, object]:
    result: dict[str, object] = {
        "intent": decision.intent,
        "intent_confidence": decision.confidence,
        "intent_reason": decision.reason,
        "intent_source": "rule",
        "intent_classification_valid": True,
    }
    if _requires_knowledge_retrieval(question):
        result["knowledge_policy"] = "required"
    return result


def _llm_result(
    question: str, intent: QueryIntent, confidence: float, reason: str, valid: bool
) -> dict[str, object]:
    result: dict[str, object] = {
        "intent": intent,
        "intent_confidence": confidence,
        "intent_reason": reason,
        "intent_source": "llm",
        "intent_classification_valid": valid,
    }
    if _requires_knowledge_retrieval(question):
        result["knowledge_policy"] = "required"
    return result


def _requires_knowledge_retrieval(question: str) -> bool:
    return any(term in question for term in ("内部资料", "公司制度", "内部知识", "政策文档", "知识库"))


def _has_data_candidates(data_context: object) -> bool:
    if not isinstance(data_context, dict):
        return False
    candidates = data_context.get("candidates")
    return isinstance(candidates, list) and bool(candidates)


def _parse_intent(content: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(content.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or set(payload) != {"intent", "confidence", "reason"}:
        return None
    try:
        confidence = float(payload["confidence"])
        if not 0.0 <= confidence <= 1.0 or not isinstance(payload["reason"], str):
            return None
        return {"intent": QueryIntent(payload["intent"]), "confidence": confidence, "reason": payload["reason"][:200]}
    except (TypeError, ValueError):
        return None
