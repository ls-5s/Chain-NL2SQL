"""Fail fast on unsafe or invalid startup settings."""

from __future__ import annotations

from urllib.parse import urlparse

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
    if settings.conversation_context_max_chars < 1000:
        raise ValueError("CONVERSATION_CONTEXT_MAX_CHARS must be at least 1000.")
    if settings.session_max_age_seconds <= 0:
        raise ValueError("APP_SESSION_MAX_AGE_SECONDS must be positive.")
    if not settings.auth_username or not settings.auth_password:
        raise ValueError("APP_AUTH_USERNAME and APP_AUTH_PASSWORD must be configured.")
    if not settings.session_secret:
        raise ValueError("APP_SESSION_SECRET must be configured.")
    if settings.app_env != "local" and settings.session_secret == "chain-nl2sql-local-session-change-me":
        raise ValueError("APP_SESSION_SECRET must be changed outside local mode.")
    if settings.app_env != "local" and settings.auth_password == "123456":
        raise ValueError("APP_AUTH_PASSWORD must be changed outside local mode.")
    if bool(settings.openai_api_key) != bool(settings.openai_model):
        raise ValueError("OPENAI_API_KEY and OPENAI_MODEL must be configured together.")
    if settings.openai_base_url:
        parsed = urlparse(settings.openai_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OPENAI_BASE_URL must be a valid HTTP or HTTPS URL.")
