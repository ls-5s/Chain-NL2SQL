"""FastAPI dependencies shared by routes."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request

from app.api.auth import require_authenticated
from app.api.authorization import AccessPolicy, local_access_policy
from app.config.settings import Settings, get_settings
from app.db.registry import DatabaseRegistry

_registries: dict[str, DatabaseRegistry] = {}


@dataclass(frozen=True)
class RequestContext:
    """携带请求关联 ID 和服务端解析出的访问策略。"""

    request_id: str
    user_id: str
    access_policy: AccessPolicy


def get_request_context(request: Request) -> RequestContext:
    settings: Settings = get_settings()
    user_id = require_authenticated(request)
    # 优先透传调用方请求 ID，便于将 API、Graph 和数据库日志关联起来。
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    registry = get_database_registry(settings)
    registrations = registry.list(enabled_only=True)
    if registrations:
        policy = AccessPolicy(
            allowed_database_ids=frozenset(item.id for item in registrations),
            allowed_tables_by_database={item.id: registry.allowed_tables(item.id) for item in registrations},
            # Keep the demo's established column and masking boundaries.
            allowed_columns_by_database={
                "demo": local_access_policy(settings).allowed_columns or {},
            },
            masked_columns_by_database={"demo": frozenset({"users.email"})},
        )
    else:
        policy = local_access_policy(settings)
    return RequestContext(
        request_id=request_id,
        user_id=user_id,
        access_policy=policy,
    )


def get_database_registry(settings: Settings | None = None) -> DatabaseRegistry:
    settings = settings or get_settings()
    path = str(settings.conversation_database_path)
    registry = _registries.get(path)
    if registry is None:
        registry = DatabaseRegistry(path, settings)
        _registries[path] = registry
    return registry
