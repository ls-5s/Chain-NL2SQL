"""本地开发环境的访问策略。

P0 不提供远程多用户访问。P1 可替换为基于 API Key 的身份和数据库授权，且不改变路由签名。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.config.settings import Settings


@dataclass(frozen=True)
class AccessPolicy:
    """请求可访问的数据范围；P1 可由 API Key/RBAC 解析后填充。"""

    allowed_database_ids: frozenset[str]
    can_view_debug_sql: bool = False
    allowed_tables: frozenset[str] = frozenset()
    allowed_columns: Mapping[str, frozenset[str]] | None = None
    masked_columns: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        # 初始化时统一策略名称，便于不区分大小写地比较 SQL 标识符。
        object.__setattr__(self, "allowed_tables", frozenset(table.lower() for table in self.allowed_tables))
        object.__setattr__(self, "masked_columns", frozenset(column.lower() for column in self.masked_columns))
        if self.allowed_columns is None:
            object.__setattr__(self, "allowed_columns", {})
        else:
            object.__setattr__(
                self,
                "allowed_columns",
                {
                    table.lower(): frozenset(column.lower() for column in columns)
                    for table, columns in self.allowed_columns.items()
                },
            )


def local_access_policy(settings: Settings) -> AccessPolicy:
    # P0 不接受客户端声明权限，只使用服务端环境变量中的白名单。
    # P0 演示环境只开放四张业务表，并对用户邮箱进行脱敏。
    return AccessPolicy(
        allowed_database_ids=settings.allowed_database_ids,
        allowed_tables=frozenset({"users", "products", "orders", "order_items"}),
        allowed_columns={
            "users": frozenset({"id", "name", "email", "created_at"}),
            "products": frozenset({"id", "name", "category", "price"}),
            "orders": frozenset({"id", "user_id", "status", "total_amount", "created_at"}),
            "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
        },
        masked_columns=frozenset({"users.email"}),
    )
