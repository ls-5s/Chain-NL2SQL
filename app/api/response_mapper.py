"""Convert graph state into API-safe responses.

The implementation is added with the graph. Keeping it separate prevents raw errors
or internal SQL from leaking through route handlers.
"""

from __future__ import annotations

from typing import Any

from app.schemas.response import QueryResponse


def map_query_state(state: dict[str, Any]) -> QueryResponse:
    # 在此处集中白名单化 State 字段，禁止路由层直接序列化内部状态。
    raise NotImplementedError("Query state mapping is implemented with the graph nodes.")
