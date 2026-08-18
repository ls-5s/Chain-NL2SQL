"""Environment-backed settings with conservative local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


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
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        # 多数据库 ID 使用逗号分隔，解析后去掉空项和重复项。
        raw_database_ids = os.getenv("ALLOWED_DATABASE_IDS", "demo")
        database_ids = frozenset(
            item.strip() for item in raw_database_ids.split(",") if item.strip()
        )
        # 模型配置保持可选，避免没有 API 密钥时健康检查和本地测试无法启动。
        return cls(
            app_env=os.getenv("APP_ENV", "local"),
            host=os.getenv("APP_HOST", "127.0.0.1"),
            port=int(os.getenv("APP_PORT", "8000")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "3")),
            query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "15")),
            result_row_limit=int(os.getenv("RESULT_ROW_LIMIT", "100")),
            allowed_database_ids=database_ids,
            openai_api_key=_optional_env("OPENAI_API_KEY"),
            openai_base_url=_optional_env("OPENAI_BASE_URL"),
            openai_model=_optional_env("OPENAI_MODEL"),
        )


@lru_cache
def get_settings() -> Settings:
    # 配置只在首次依赖注入时读取，保证同一进程内行为一致。
    return Settings.from_env()


def _optional_env(name: str) -> str | None:
    # 空字符串和全空白配置统一视为未配置，避免把无效值传给 SDK。
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None
