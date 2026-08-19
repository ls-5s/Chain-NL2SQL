"""LLM intent gate that runs before Schema retrieval."""

from __future__ import annotations

import json

from app.graph.state import NL2SQLState
from app.llm.client import LLMClient
from app.llm.prompts import build_intent_classification_prompt
from app.schemas.domain import QueryIntent


def make_intent_gate_node(llm_client: LLMClient, timeout_seconds: float):
    prompt_template = build_intent_classification_prompt()

    def classify(state: NL2SQLState) -> dict[str, object]:
        response = llm_client.generate(
            prompt_template.invoke({"question": state["question"]}),
            timeout_seconds=timeout_seconds,
        )
        intent = _parse_intent(response.content)
        if intent is None:
            return {
                "intent": QueryIntent.CLARIFICATION,
                "intent_classification_valid": False,
            }
        return {"intent": intent, "intent_classification_valid": True}

    return classify


def _parse_intent(content: str) -> QueryIntent | None:
    try:
        payload = json.loads(content.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or set(payload) != {"intent"}:
        return None
    try:
        return QueryIntent(payload["intent"])
    except (TypeError, ValueError):
        return None
