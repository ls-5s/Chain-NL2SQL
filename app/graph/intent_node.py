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
        context_follow_up = _is_database_follow_up(state["question"], state.get("conversation_context", ""))
        if context_follow_up:
            # Elliptical follow-ups such as "推荐一篇" are data requests when
            # the current conversation already contains an article result.
            return {
                "intent": QueryIntent.DATA_QUERY,
                "intent_confidence": 0.93,
                "intent_reason": "结合当前会话中的数据库结果理解省略主语或指代",
                "intent_source": "conversation_context",
                "intent_classification_valid": True,
            }
        if rule_decision is not None:
            result = {
                "intent": rule_decision.intent,
                "intent_confidence": rule_decision.confidence,
                "intent_reason": rule_decision.reason,
                "intent_source": "rule",
                "intent_classification_valid": True,
            }
            if any(term in state["question"] for term in ("内部资料", "公司制度", "内部知识", "政策文档", "知识库")):
                result["knowledge_policy"] = "required"
            return result
        response = llm_client.generate(
            prompt_template.invoke({"question": state["question"], "conversation_context": state.get("conversation_context", "")}),
            timeout_seconds=timeout_seconds,
        )
        parsed = _parse_intent(response.content)
        if parsed is None or parsed["confidence"] < confidence_threshold:
            result = {
                "intent": QueryIntent.CLARIFY,
                "intent_confidence": parsed["confidence"] if parsed else 0.0,
                "intent_reason": "LLM 分类置信度不足或输出格式无效",
                "intent_source": "llm",
                "intent_classification_valid": False,
            }
            if any(term in state["question"] for term in ("内部资料", "公司制度", "内部知识", "政策文档", "知识库")):
                result["knowledge_policy"] = "required"
            return result
        result = {
            "intent": parsed["intent"],
            "intent_confidence": parsed["confidence"],
            "intent_reason": parsed["reason"],
            "intent_source": "llm",
            "intent_classification_valid": True,
        }
        if any(term in state["question"] for term in ("内部资料", "公司制度", "内部知识", "政策文档", "知识库")):
            result["knowledge_policy"] = "required"
        return result

    return classify


def _is_database_follow_up(question: str, conversation_context: str) -> bool:
    """Recognize short follow-ups that refer to a previous database result."""

    if not conversation_context or not question.strip():
        return False
    normalized = " ".join(question.strip().split()).lower()
    # Do not reinterpret explicit meta questions about the chat itself.
    if any(pattern in normalized for pattern in ("上一个问题是什么", "刚才问了什么", "之前问了什么")):
        return False
    has_follow_up_language = any(
        marker in normalized
        for marker in ("推荐", "一篇", "一个", "这篇", "这类", "这些", "刚才", "继续", "数据库里面", "数据库里的")
    )
    has_article_result = any(marker in conversation_context.lower() for marker in ("articles", "文章", "generated_sql"))
    return has_follow_up_language and has_article_result


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
