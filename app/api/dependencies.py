"""FastAPI dependencies shared by routes."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request

from app.api.auth import require_authenticated
from app.api.authorization import AccessPolicy, local_access_policy
from app.config.settings import Settings, get_settings


@dataclass(frozen=True)
class RequestContext:
    """携带请求关联 ID 和服务端解析出的访问策略。"""

    request_id: str
    user_id: str
    access_policy: AccessPolicy


def get_request_context(request: Request) -> RequestContext:
    settings: Settings = get_settings()
    # 优先透传调用方请求 ID，便于将 API、Graph 和数据库日志关联起来。
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    return RequestContext(
        request_id=request_id,
        user_id=require_authenticated(request),
        access_policy=local_access_policy(settings),
    )
