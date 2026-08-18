"""Domain models that are safe to expose outside the graph."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryStatus(str, Enum):
    """查询工作流的终态和运行态枚举。"""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"


class ErrorCategory(str, Enum):
    """可安全返回给调用方的稳定错误分类。"""

    SYNTAX_ERROR = "syntax_error"
    UNKNOWN_COLUMN = "unknown_column"
    UNKNOWN_TABLE = "unknown_table"
    JOIN_ERROR = "join_error"
    AGGREGATION_ERROR = "aggregation_error"
    INVALID_MODEL_OUTPUT = "invalid_model_output"
    PERMISSION_ERROR = "permission_error"
    CONNECTION_ERROR = "connection_error"
    UNSAFE_SQL = "unsafe_sql"
    SCHEMA_CHANGED = "schema_changed"
    UNKNOWN = "unknown"


class QueryResult(BaseModel):
    """经数据库策略过滤、截断且可以安全序列化的查询结果。"""

    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False


class TraceEvent(BaseModel):
    """仅保存可展示的节点摘要，原始异常不得写入该模型。"""

    node: str
    iteration: int
    duration_ms: int | None = None
    error_category: ErrorCategory | None = None
    retrieved_document_count: int | None = None


class SchemaDocument(BaseModel):
    """供模型使用的单表 Schema 上下文。"""

    table_name: str
    content: str
    database_id: str
    column_names: list[str] = Field(default_factory=list)


class SchemaRetrieval(BaseModel):
    """一次请求固定使用的 Schema 文档及其版本指纹。"""

    documents: list[SchemaDocument]
    schema_version: str
