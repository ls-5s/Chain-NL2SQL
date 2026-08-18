"""Environment-backed settings with conservative local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """运行期间只读的应用配置，避免节点间共享可变全局状态。"""

    app_env: str
    host: str
    port: int
    max_iterations: int
    query_timeout_seconds: int
    result_row_limit: int
    allowed_database_ids: frozenset[str]

    @classmethod
    def from_env(cls) -> "Settings":
        # 多数据库 ID 使用逗号分隔，解析后去掉空项和重复项。
        raw_database_ids = os.getenv("ALLOWED_DATABASE_IDS", "demo")
        database_ids = frozenset(
            item.strip() for item in raw_database_ids.split(",") if item.strip()
        )
        return cls(
            app_env=os.getenv("APP_ENV", "local"),
            host=os.getenv("APP_HOST", "127.0.0.1"),
            port=int(os.getenv("APP_PORT", "8000")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "3")),
            query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "15")),
            result_row_limit=int(os.getenv("RESULT_ROW_LIMIT", "100")),
            allowed_database_ids=database_ids,
        )


@lru_cache
def get_settings() -> Settings:
    # 配置只在首次依赖注入时读取，保证同一进程内行为一致。
    return Settings.from_env()
