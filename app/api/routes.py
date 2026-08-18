"""HTTP routes for the P0 application shell."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import RequestContext, get_request_context
from app.config.settings import Settings, get_settings
from app.schemas.request import QueryRequest
from app.schemas.response import DatabaseListResponse, HealthResponse, QueryResponse

# 业务接口和进程健康检查分组，便于后续分别配置鉴权和监控。
api_router = APIRouter(prefix="/api/v1", tags=["nl2sql"])
system_router = APIRouter(tags=["system"])


@system_router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    # 不暴露模型、数据库连接等敏感配置，只报告可安全展示的运行环境。
    return HealthResponse(environment=settings.app_env)


@api_router.get("/databases", response_model=DatabaseListResponse)
def list_databases(settings: Settings = Depends(get_settings)) -> DatabaseListResponse:
    # 数据库 ID 来自服务端白名单，不能由客户端自由枚举连接配置。
    return DatabaseListResponse(database_ids=sorted(settings.allowed_database_ids))


@api_router.post("/query", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    context: RequestContext = Depends(get_request_context),
) -> QueryResponse:
    # 在编排图启动前阻断未授权数据库，避免请求到达底层执行器。
    if payload.database_id not in context.access_policy.allowed_database_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Database is not allowed.")
    # 骨架阶段明确返回 501，防止空实现被误用为可执行的 NL2SQL 服务。
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="The LangGraph query workflow has not been implemented yet.",
    )
