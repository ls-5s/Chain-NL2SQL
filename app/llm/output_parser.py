"""Normalize a model response before SQL validation."""

from __future__ import annotations

import re


def extract_sql(content: str) -> str | None:
    # 允许模型用 Markdown 围栏包裹 SQL，但不把围栏传入 AST 校验器。
    candidate = re.sub(r"^```(?:sql)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    # 多语句输出交给上游作为 invalid_model_output 处理，不能进入数据库层。
    if not candidate or ";" in candidate.rstrip(";"):
        return None
    return candidate.rstrip(";")
