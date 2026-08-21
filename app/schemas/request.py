"""Incoming API request models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """用户提交给 NL2SQL 工作流的最小请求体。"""

    question: str = Field(min_length=1, max_length=2_000)
    database_id: str = Field(min_length=1, max_length=100)
    max_iterations: int | None = Field(default=None, ge=1, le=10)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class ConversationCreateRequest(BaseModel):
    database_id: str = Field(min_length=1, max_length=100)


class ConversationQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    max_iterations: int | None = Field(default=None, ge=1, le=10)
    reference_ids: list[str] = Field(default_factory=list, max_length=5)


class ResultReferenceRequest(BaseModel):
    turn_id: str = Field(min_length=1, max_length=64)
    row_index: int = Field(ge=0, le=99)
