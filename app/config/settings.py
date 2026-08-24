"""Environment-backed settings with conservative local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str
    host: str
    port: int
    max_iterations: int
    query_timeout_seconds: int
    result_row_limit: int
    result_summary_enabled: bool = True
    result_summary_max_chars: int = 12000
    intent_confidence_threshold: float = 0.75
    demo_database_path: str = "data/demo.sqlite"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    # LangSmith tracing is opt-in so local development does not make network calls by accident.
    langsmith_tracing: bool = False
    langsmith_endpoint: str | None = None
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None
    schema_retrieval_mode: str = "hybrid"
    schema_top_k: int = 5
    # Keep generated runtime indexes separate from repository snapshots that may be read-only.
    schema_index_root: str = "data/schema_metadata_runtime"
    schema_fallback_mode: str = "bm25"
    schema_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    schema_reranker_model: str = "BAAI/bge-reranker-base"
    conversation_database_path: str = "data/conversations.sqlite3"
    conversation_context_max_chars: int = 6000
    knowledge_root: str = "data/knowledge"
    knowledge_database_path: str = "data/knowledge.sqlite3"
    knowledge_top_k: int = 5
    knowledge_max_upload_bytes: int = 20 * 1024 * 1024
    knowledge_chunk_size: int = 800
    knowledge_chunk_overlap: int = 120
    auth_username: str = "admin"
    auth_password: str = "123456"
    session_secret: str = "chain-nl2sql-local-session-change-me"
    session_max_age_seconds: int = 60 * 60 * 24 * 14

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "local"),
            host=os.getenv("APP_HOST", "127.0.0.1"),
            port=int(os.getenv("APP_PORT", "8000")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "3")),
            query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "15")),
            result_row_limit=int(os.getenv("RESULT_ROW_LIMIT", "100")),
            result_summary_enabled=_env_bool(os.getenv("RESULT_SUMMARY_ENABLED", "true")),
            result_summary_max_chars=int(os.getenv("RESULT_SUMMARY_MAX_CHARS", "12000")),
            intent_confidence_threshold=float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.75")),
            demo_database_path=os.getenv("DEMO_DATABASE_PATH", "data/demo.sqlite"),
            openai_api_key=_optional_env("OPENAI_API_KEY"),
            openai_base_url=_optional_env("OPENAI_BASE_URL"),
            openai_model=_optional_env("OPENAI_MODEL"),
            langsmith_tracing=_env_bool(
                os.getenv("LANGSMITH_TRACING", os.getenv("LANGCHAIN_TRACING_V2", "false"))
            ),
            langsmith_endpoint=_optional_env("LANGSMITH_ENDPOINT"),
            langsmith_api_key=_optional_env("LANGSMITH_API_KEY") or _optional_env("LANGCHAIN_API_KEY"),
            langsmith_project=_optional_env("LANGSMITH_PROJECT") or _optional_env("LANGCHAIN_PROJECT"),
            schema_retrieval_mode=os.getenv("SCHEMA_RETRIEVAL_MODE", "hybrid"),
            schema_top_k=int(os.getenv("SCHEMA_TOP_K", "5")),
            schema_index_root=os.getenv("SCHEMA_INDEX_ROOT", "data/schema_metadata_runtime"),
            schema_fallback_mode=os.getenv("SCHEMA_FALLBACK_MODE", "bm25"),
            schema_embedding_model=os.getenv("SCHEMA_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
            schema_reranker_model=os.getenv("SCHEMA_RERANKER_MODEL", "BAAI/bge-reranker-base"),
            conversation_database_path=os.getenv("CONVERSATION_DATABASE_PATH", "data/conversations.sqlite3"),
            conversation_context_max_chars=int(os.getenv("CONVERSATION_CONTEXT_MAX_CHARS", "6000")),
            knowledge_root=os.getenv("KNOWLEDGE_ROOT", "data/knowledge"),
            knowledge_database_path=os.getenv("KNOWLEDGE_DATABASE_PATH", "data/knowledge.sqlite3"),
            knowledge_top_k=int(os.getenv("KNOWLEDGE_TOP_K", "5")),
            knowledge_max_upload_bytes=int(os.getenv("KNOWLEDGE_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))),
            knowledge_chunk_size=int(os.getenv("KNOWLEDGE_CHUNK_SIZE", "800")),
            knowledge_chunk_overlap=int(os.getenv("KNOWLEDGE_CHUNK_OVERLAP", "120")),
            auth_username=os.getenv("APP_AUTH_USERNAME", "admin"),
            auth_password=os.getenv("APP_AUTH_PASSWORD", "123456"),
            session_secret=os.getenv("APP_SESSION_SECRET", "chain-nl2sql-local-session-change-me"),
            session_max_age_seconds=int(os.getenv("APP_SESSION_MAX_AGE_SECONDS", str(60 * 60 * 24 * 14))),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _env_bool(value: str | None) -> bool:
    """Parse environment booleans without treating arbitrary text as enabled."""

    return (value or "").strip().lower() in {"1", "true", "yes", "on"}
