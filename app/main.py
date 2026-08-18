"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import api_router, system_router
from app.config.settings import get_settings
from app.config.validation import validate_settings


def create_app() -> FastAPI:
    settings = get_settings()
    # 在创建路由前校验配置，避免服务启动后才暴露不安全的配置错误。
    validate_settings(settings)
    app = FastAPI(title="Chain-NL2SQL", version="0.1.0")
    app.include_router(system_router)
    app.include_router(api_router)
    return app


app = create_app()
