"""Pure conditional routing functions for the query graph."""

from __future__ import annotations

from typing import Literal

from app.schemas.domain import ErrorCategory


# 只有 SQL 内容问题允许进入修复；权限、连接和安全错误必须直接终止。
REPAIRABLE_ERRORS = {
    ErrorCategory.SYNTAX_ERROR,
    ErrorCategory.UNKNOWN_COLUMN,
    ErrorCategory.UNKNOWN_TABLE,
    ErrorCategory.JOIN_ERROR,
    ErrorCategory.AGGREGATION_ERROR,
    ErrorCategory.INVALID_MODEL_OUTPUT,
}


def should_repair(
    *, error_category: ErrorCategory | None, iteration: int, max_iterations: int
) -> bool:
    # max_iterations 包含首次尝试，因此下一轮必须仍在上限以内。
    return error_category in REPAIRABLE_ERRORS and iteration + 1 < max_iterations


def route_after_execution(succeeded: bool) -> Literal["finalize", "classify_error"]:
    return "finalize" if succeeded else "classify_error"
