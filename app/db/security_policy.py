"""SQL safety boundary.

The concrete implementation will parse SQL with sqlglot and apply read-only plus
data-access policy checks before a database adapter executes it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SQLValidationResult:
    """安全策略的结构化判定结果，拒绝原因可用于安全错误响应。"""

    allowed: bool
    reason: str | None = None


def validate_readonly_sql(sql: str, dialect: str) -> SQLValidationResult:
    # 实现时必须使用 sqlglot AST，而不是仅依赖危险关键字黑名单。
    raise NotImplementedError("Implement sqlglot AST validation in the P0 security task.")
