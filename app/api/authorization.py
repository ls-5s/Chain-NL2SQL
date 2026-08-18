"""Local-development access policy placeholder.

P0 has no remote multi-user access. P1 can replace this module with API-key based
principal and database authorization without changing route signatures.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import Settings


@dataclass(frozen=True)
class AccessPolicy:
    """请求可访问的数据范围；P1 可由 API Key/RBAC 解析后填充。"""

    allowed_database_ids: frozenset[str]
    can_view_debug_sql: bool = False


def local_access_policy(settings: Settings) -> AccessPolicy:
    # P0 不接受客户端声明权限，只使用服务端环境变量中的白名单。
    return AccessPolicy(allowed_database_ids=settings.allowed_database_ids)
