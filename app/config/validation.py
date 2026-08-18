"""Fail fast on unsafe or invalid startup settings."""

from __future__ import annotations

from app.config.settings import Settings


def validate_settings(settings: Settings) -> None:
    # P0 只允许本机绑定，避免未实现鉴权时暴露调试服务。
    if settings.app_env == "local" and settings.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Local mode must bind to 127.0.0.1 or localhost.")
    # 限制修复轮次，防止模型错误时产生无限调用和费用失控。
    if not 1 <= settings.max_iterations <= 10:
        raise ValueError("MAX_ITERATIONS must be between 1 and 10.")
    if settings.query_timeout_seconds <= 0:
        raise ValueError("QUERY_TIMEOUT_SECONDS must be positive.")
    if settings.result_row_limit <= 0:
        raise ValueError("RESULT_ROW_LIMIT must be positive.")
    if not settings.allowed_database_ids:
        raise ValueError("At least one database id must be configured.")
