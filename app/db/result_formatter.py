"""应用行数限制、字段脱敏并格式化为 API 安全结果。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.api.authorization import AccessPolicy
from app.schemas.domain import QueryResult


def format_query_result(
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    result_row_limit: int,
    access_policy: AccessPolicy,
) -> QueryResult:
    # 多读取一行，用于区分完整结果和被截断的结果。
    visible_rows = [list(row) for row in rows[: result_row_limit + 1]]
    # 不把用于判断截断的哨兵行返回给调用方。
    truncated = len(visible_rows) > result_row_limit
    visible_rows = visible_rows[:result_row_limit]
    # 同时匹配 email 和 users.email 这样的全限定策略名称。
    masked_names = {
        field.rsplit(".", 1)[-1].lower() for field in access_policy.masked_columns
    }
    # 读取后再统一脱敏，避免数据库结果直接控制 API 可见性。
    for row in visible_rows:
        for index, column in enumerate(columns):
            if column.lower() in masked_names and index < len(row):
                row[index] = "***"
    # 返回供后续 Graph 和 API 层使用的稳定领域模型。
    return QueryResult(
        columns=list(columns),
        rows=visible_rows,
        row_count=len(visible_rows),
        truncated=truncated,
    )
