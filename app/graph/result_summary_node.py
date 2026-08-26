from __future__ import annotations

import json
import re
from html import unescape
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
        # A truncated result is not a complete basis for a row-by-row model
        # summary. Use the deterministic count message so the answer cannot
        # describe a smaller sample as if it were the displayed result set.
        if state.get("status") != QueryStatus.SUCCEEDED or result is None or not enabled or result.truncated:
            return base
        try:
            if max_chars <= 0:
                return base
            result_json = _serialize_result(result, max_chars)
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
    if result and result.rows and "推荐" in question and not _is_summary_request(question):
        title_index = next(
            (index for index, column in enumerate(result.columns) if any(marker in column.lower() for marker in ("title", "name", "标题", "名称"))),
            None,
        )
        if title_index is not None:
            title = str(result.rows[0][title_index]).strip()
            if title:
                return f"推荐这篇：{title}。"
    if result and result.rows and _is_summary_request(question):
        title_index = _find_column(result, ("title", "name", "标题", "名称"))
        content_index = _find_column(result, ("content", "description", "summary", "excerpt", "正文", "内容", "摘要"))
        if title_index is not None:
            lines = []
            for row in result.rows:
                title = _clean_text(row[title_index])
                if not title:
                    continue
                excerpt = _clean_text(row[content_index])[:140] if content_index is not None else ""
                lines.append(f"- {title}" + (f"：{excerpt}…" if excerpt else ""))
            if lines:
                return "各篇文章摘要：\n" + "\n".join(lines)
    count = result.row_count if result else 0
    suffix = "（结果已按安全策略截断）" if result and result.truncated else ""
    return f"查询完成，共返回 {count} 行结果。{suffix}"


def _serialize_result(result: QueryResult, max_chars: int | None = None) -> str:
    payload = {
        "columns": result.columns,
        "rows": result.rows,
        "row_count": result.row_count,
        "truncated": result.truncated,
    }
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=_json_default)
    if max_chars is None or len(serialized) <= max_chars:
        return serialized
    # First preserve the complete row set while shortening long text fields.
    # This keeps summaries useful for normal-sized results and still lets the
    # model see real values instead of empty placeholders.
    for cell_chars in (700, 400, 220, 100, 40):
        compact_rows = [[_clean_text(value)[:cell_chars] for value in row] for row in result.rows]
        compact = {**payload, "rows": compact_rows}
        serialized = json.dumps(compact, ensure_ascii=False, separators=(",", ":"), default=_json_default)
        if len(serialized) <= max_chars:
            return serialized

    # Very wide result sets need a bounded sample. Keep the first rows and
    # explicitly tell the summarizer how many rows were omitted.
    row_limits = [len(result.rows)]
    while row_limits[-1] > 1:
        next_limit = max(1, row_limits[-1] // 2)
        if next_limit == row_limits[-1]:
            break
        row_limits.append(next_limit)
    for row_limit in row_limits[1:]:
        for cell_chars in (220, 100, 40, 20):
            compact_rows = [[_clean_text(value)[:cell_chars] for value in row] for row in result.rows[:row_limit]]
            compact = {
                **payload,
                "rows": compact_rows,
                "rows_shown": row_limit,
                "rows_omitted": max(0, len(result.rows) - row_limit),
            }
            serialized = json.dumps(compact, ensure_ascii=False, separators=(",", ":"), default=_json_default)
            if len(serialized) <= max_chars:
                return serialized
    # The column names and row count are still valid JSON even for an
    # unusually wide result set that cannot fit the configured budget.
    return json.dumps(
        {
            "columns": result.columns,
            "rows": [],
            "row_count": result.row_count,
            "truncated": True,
            "rows_shown": 0,
            "rows_omitted": len(result.rows),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _is_summary_request(question: str) -> bool:
    return any(marker in question for marker in ("总结", "摘要", "概括", "分别介绍", "每篇", "各篇"))


def _find_column(result: QueryResult, markers: tuple[str, ...]) -> int | None:
    return next(
        (index for index, column in enumerate(result.columns) if any(marker in column.lower() for marker in markers)),
        None,
    )


def _clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unescape(re.sub(r"<[^>]*>", " ", text))
    return " ".join(text.split())


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return "<binary>"
    return str(value)
