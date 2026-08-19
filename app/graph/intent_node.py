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
        rule_decision = classify_by_rules(state["question"])
        if rule_decision is not None:
            return {
                "intent": rule_decision.intent,
                "intent_confidence": rule_decision.confidence,
                "intent_reason": rule_decision.reason,
                "intent_source": "rule",
                "intent_classification_valid": True,
            }
        response = llm_client.generate(
            prompt_template.invoke({"question": state["question"]}),
            timeout_seconds=timeout_seconds,
        )
        parsed = _parse_intent(response.content)
        if parsed is None or parsed["confidence"] < confidence_threshold:
            return {
                "intent": QueryIntent.CLARIFICATION,
                "intent_confidence": parsed["confidence"] if parsed else 0.0,
                "intent_reason": "LLM 分类置信度不足或输出格式无效",
                "intent_source": "llm",
                "intent_classification_valid": False,
            }
        return {
            "intent": parsed["intent"],
            "intent_confidence": parsed["confidence"],
            "intent_reason": parsed["reason"],
            "intent_source": "llm",
            "intent_classification_valid": True,
        }

    return classify


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
