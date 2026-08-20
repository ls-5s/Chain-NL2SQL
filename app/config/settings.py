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
    allowed_database_ids: frozenset[str]
    intent_confidence_threshold: float = 0.75
    demo_database_path: str = "data/demo.sqlite"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    schema_retrieval_mode: str = "hybrid"
    schema_top_k: int = 5
    schema_index_root: str = "data/schema_metadata"
    schema_fallback_mode: str = "bm25"
    schema_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    schema_reranker_model: str = "BAAI/bge-reranker-base"

    @classmethod
    def from_env(cls) -> "Settings":
        raw_database_ids = os.getenv("ALLOWED_DATABASE_IDS", "demo")
        database_ids = frozenset(item.strip() for item in raw_database_ids.split(",") if item.strip())
        return cls(
            app_env=os.getenv("APP_ENV", "local"),
            host=os.getenv("APP_HOST", "127.0.0.1"),
            port=int(os.getenv("APP_PORT", "8000")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "3")),
            query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "15")),
            result_row_limit=int(os.getenv("RESULT_ROW_LIMIT", "100")),
            allowed_database_ids=database_ids,
            intent_confidence_threshold=float(os.getenv("INTENT_CONFIDENCE_THRESHOLD", "0.75")),
            demo_database_path=os.getenv("DEMO_DATABASE_PATH", "data/demo.sqlite"),
            openai_api_key=_optional_env("OPENAI_API_KEY"),
            openai_base_url=_optional_env("OPENAI_BASE_URL"),
            openai_model=_optional_env("OPENAI_MODEL"),
            schema_retrieval_mode=os.getenv("SCHEMA_RETRIEVAL_MODE", "hybrid"),
            schema_top_k=int(os.getenv("SCHEMA_TOP_K", "5")),
            schema_index_root=os.getenv("SCHEMA_INDEX_ROOT", "data/schema_metadata"),
            schema_fallback_mode=os.getenv("SCHEMA_FALLBACK_MODE", "bm25"),
            schema_embedding_model=os.getenv("SCHEMA_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
            schema_reranker_model=os.getenv("SCHEMA_RERANKER_MODEL", "BAAI/bge-reranker-base"),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None
