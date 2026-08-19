"""LangChain tool adapters for controlled database access."""

from __future__ import annotations

import math
import time
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, field_validator

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutionError, DatabaseExecutor


class QueryDatabaseInput(BaseModel):
    """The only model-controlled values accepted by the query tool."""

    sql: str = Field(min_length=1, max_length=20_000)
    parameters: list[Any] = Field(default_factory=list, max_length=100)

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, values: list[Any]) -> list[Any]:
        for value in values:
            if value is None or isinstance(value, (str, bool, int)):
                if isinstance(value, str) and len(value) > 2_000:
                    raise ValueError("String parameters must not exceed 2,000 characters.")
                continue
            if isinstance(value, float) and math.isfinite(value):
                continue
            raise ValueError("Parameters must be finite JSON scalar values.")
        return values


def create_query_database_tool(
    *,
    database_executor: DatabaseExecutor,
    access_policy: AccessPolicy,
    timeout_seconds: float,
) -> StructuredTool:
    """Create a model-callable read-only query tool with fixed server policy."""

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    def query_database(sql: str, parameters: list[Any] | None = None) -> dict[str, Any]:
        """Execute one parameterized, read-only SQL statement against the allowed database."""

        try:
            result = database_executor.execute_readonly(
                sql,
                time.monotonic() + timeout_seconds,
                access_policy,
                tuple(parameters or ()),
            )
        except DatabaseExecutionError as error:
            # Tool callers get the same stable, redacted errors as the Graph.
            return {
                "ok": False,
                "error_category": error.category,
                "message": error.safe_message,
            }
        return {"ok": True, "result": result.model_dump(mode="json")}

    return StructuredTool.from_function(
        func=query_database,
        name="query_database",
        description=(
            "Execute exactly one parameterized, read-only SQL query against the current allowed database. "
            "Use only after selecting allowed tables and columns. Write operations and unsafe SQL are rejected."
        ),
        args_schema=QueryDatabaseInput,
    )
