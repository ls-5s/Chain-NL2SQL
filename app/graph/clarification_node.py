from __future__ import annotations

from app.graph.state import NL2SQLState
from app.schemas.domain import AnswerSource, QueryIntent, QueryStatus


def make_clarification_node():
    def clarify(state: NL2SQLState) -> dict[str, object]:
        fields = list(state.get("clarification_fields", []))
        if not fields:
            fields = ["业务对象", "指标或操作", "时间范围"]
        actions = list(state.get("required_actions", [])) or ["provide_fields"]
        if state.get("intent") == QueryIntent.DATA_QUERY and not state.get("database_id"):
            fields = ["数据库"]
            actions = ["select_database"]
        return {
            "status": QueryStatus.NEEDS_CLARIFICATION,
            "clarification_fields": fields,
            "required_actions": actions,
            "pending_clarification": {"question": state.get("question", ""), "fields": fields, "required_actions": actions},
            "final_answer": "为了继续处理，请补充：" + "、".join(fields) + "。",
            "answer_source": AnswerSource.DETERMINISTIC_FALLBACK,
        }

    return clarify
