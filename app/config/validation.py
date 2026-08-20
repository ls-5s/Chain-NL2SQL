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
    if not 0.0 < settings.intent_confidence_threshold <= 1.0:
        raise ValueError("INTENT_CONFIDENCE_THRESHOLD must be between 0 and 1.")
    if not settings.allowed_database_ids:
        raise ValueError("At least one database id must be configured.")
    if settings.schema_retrieval_mode not in {"vector", "bm25", "hybrid"}:
        raise ValueError("SCHEMA_RETRIEVAL_MODE must be vector, bm25, or hybrid.")
    if settings.schema_fallback_mode not in {"none", "bm25"}:
        raise ValueError("SCHEMA_FALLBACK_MODE must be none or bm25.")
    if not 1 <= settings.schema_top_k <= 50:
        raise ValueError("SCHEMA_TOP_K must be between 1 and 50.")
