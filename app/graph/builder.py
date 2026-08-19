"""Minimal LangGraph workflow for safe NL2SQL execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutor
from app.graph.execution_node import make_execution_node
from app.graph.finalize_node import make_finalize_node
from app.graph.generation_node import make_generation_node
from app.graph.state import NL2SQLState
from app.graph.validation_node import make_validation_node
from app.llm.client import LLMClient
from app.rag.retriever import SchemaRetriever


def build_query_graph(
    *,
    database_executor: DatabaseExecutor,
    llm_client: LLMClient,
    schema_retriever: SchemaRetriever,
    access_policy: AccessPolicy,
    query_timeout_seconds: float,
    llm_timeout_seconds: float | None = None,
) -> Any:
    graph = StateGraph(NL2SQLState)
    graph.add_node("retrieve_schema", _retrieve_schema_node(schema_retriever))
    graph.add_node("generate_sql", make_generation_node(llm_client, llm_timeout_seconds or query_timeout_seconds))
    graph.add_node("validate_sql", make_validation_node(access_policy))
    graph.add_node("execute_sql", make_execution_node(database_executor, access_policy, query_timeout_seconds))
    graph.add_node("finalize", make_finalize_node())
    graph.set_entry_point("retrieve_schema")
    graph.add_edge("retrieve_schema", "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_edge("validate_sql", "execute_sql")
    graph.add_edge("execute_sql", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def _retrieve_schema_node(retriever: SchemaRetriever):
    def retrieve(state: NL2SQLState) -> dict[str, object]:
        retrieval = retriever.retrieve(state["question"], state["database_id"])
        return {"schema_version": retrieval.schema_version, "schema_context": retrieval.documents}

    return retrieve


class SQLiteSchemaRetriever:
    def __init__(self, database_executor: DatabaseExecutor) -> None:
        self.database_executor = database_executor

    def retrieve(self, question: str, database_id: str):
        return self.database_executor.inspect_schema(database_id)
