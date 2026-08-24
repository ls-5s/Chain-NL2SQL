from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.graph.state import NL2SQLState
from app.llm.client import LLMClient
from app.llm.prompts import build_result_summary_prompt
from app.schemas.domain import AnswerSource, QueryStatus, QueryResult, TraceEvent


def make_result_summary_node(
    llm_client: LLMClient,
    timeout_seconds: float,
    *,
    enabled: bool = True,
    max_chars: int = 12000,
):
    prompt_template = build_result_summary_prompt()

    def summarize(state: NL2SQLState) -> dict[str, object]:
        result = state.get("query_result")
        fallback = _fallback(result, state.get("question", ""))
        base = {
            "final_answer": fallback,
            "answer_source": AnswerSource.DETERMINISTIC_FALLBACK,
            "trace": state.get("trace", [])
            + [TraceEvent(node="summarize_result", iteration=state["iteration"])],
        }
        if state.get("status") != QueryStatus.SUCCEEDED or result is None or not enabled:
            return base
        try:
            result_json = _serialize_result(result)
            if max_chars <= 0 or len(result_json) > max_chars:
                return base
            response = llm_client.generate(
                prompt_template.invoke({
                    "question": state["question"],
                    "result_json": result_json,
                }),
                timeout_seconds=timeout_seconds,
            )
            answer = response.content.strip()
            if not answer or len(answer) > max_chars:
                return base
        except Exception:
            # A summary is presentation-only; never turn a successful query
            # into an error because the optional model call failed.
            return base
        return {
            "final_answer": answer,
            "answer_source": AnswerSource.RESULT_SUMMARY,
            "trace": base["trace"],
        }

    return summarize


def _fallback(result: QueryResult | None, question: str = "") -> str:
    if result and result.rows and any(marker in question for marker in ("推荐", "一篇", "一个")):
        title_index = next(
            (index for index, column in enumerate(result.columns) if any(marker in column.lower() for marker in ("title", "name", "标题", "名称"))),
            None,
        )
        if title_index is not None:
            title = str(result.rows[0][title_index]).strip()
            if title:
                return f"推荐这篇：{title}。"
    count = result.row_count if result else 0
    suffix = "（结果已按安全策略截断）" if result and result.truncated else ""
    return f"查询完成，共返回 {count} 行结果。{suffix}"


def _serialize_result(result: QueryResult) -> str:
    payload = {
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "truncated": result.truncated,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return "<binary>"
    return str(value)
