"""Minimal LangGraph workflow for safe NL2SQL execution."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutor
from app.graph.clarification_node import make_clarification_node
from app.graph.execution_node import make_execution_node
from app.graph.finalize_node import make_finalize_node
from app.graph.general_answer_node import make_general_answer_node
from app.graph.generation_node import make_generation_node
from app.graph.intent_node import make_intent_gate_node
from app.graph.state import NL2SQLState
from app.graph.validation_node import make_validation_node
from app.llm.client import LLMClient
from app.rag.retriever import SchemaRetriever
from app.schemas.domain import QueryIntent


def build_query_graph(
    *,
    database_executor: DatabaseExecutor,
    llm_client: LLMClient,
    schema_retriever: SchemaRetriever,
    access_policy: AccessPolicy,
    query_timeout_seconds: float,
    llm_timeout_seconds: float | None = None,
) -> Any:
    model_timeout_seconds = llm_timeout_seconds or query_timeout_seconds
    graph = StateGraph(NL2SQLState)
    graph.add_node("intent_gate", make_intent_gate_node(llm_client, model_timeout_seconds))
    graph.add_node("retrieve_schema", _retrieve_schema_node(schema_retriever))
    graph.add_node("generate_sql", make_generation_node(llm_client, model_timeout_seconds))
    graph.add_node("validate_sql", make_validation_node(access_policy))
    graph.add_node("execute_sql", make_execution_node(database_executor, access_policy, query_timeout_seconds))
    graph.add_node("general_answer", make_general_answer_node(llm_client, model_timeout_seconds))
    graph.add_node("clarify", make_clarification_node(llm_client, model_timeout_seconds))
    graph.add_node("finalize", make_finalize_node())
    graph.set_entry_point("intent_gate")
    graph.add_conditional_edges(
        "intent_gate",
        _route_after_intent,
        {
            QueryIntent.DATA_QUERY.value: "retrieve_schema",
            QueryIntent.GENERAL_CHAT.value: "general_answer",
            QueryIntent.CLARIFICATION.value: "clarify",
        },
    )
    graph.add_edge("retrieve_schema", "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_edge("validate_sql", "execute_sql")
    graph.add_edge("execute_sql", "finalize")
    graph.add_edge("general_answer", "finalize")
    graph.add_edge("clarify", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def _route_after_intent(state: NL2SQLState) -> str:
    intent = state.get("intent", QueryIntent.CLARIFICATION)
    return intent.value if isinstance(intent, QueryIntent) else str(intent)


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
