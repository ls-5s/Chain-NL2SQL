"""Configure LangSmith/LangChain tracing from application settings."""

from __future__ import annotations

import os

from app.config.settings import Settings


def configure_langsmith(settings: Settings) -> None:
    """Apply tracing settings before any graph or model invocation is created.

    LangGraph and ChatOpenAI discover tracing through environment variables. Keeping
    this in one place also supports the legacy ``LANGCHAIN_*`` variable names.
    """

    enabled = "true" if settings.langsmith_tracing else "false"
    os.environ["LANGSMITH_TRACING"] = enabled
    os.environ["LANGCHAIN_TRACING_V2"] = enabled
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    if settings.langsmith_project:
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
