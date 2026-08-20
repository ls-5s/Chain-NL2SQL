"""Minimal LangGraph workflow for safe NL2SQL execution."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutionError, DatabaseExecutor
from app.graph.clarification_node import make_clarification_node
from app.graph.execution_node import make_execution_node
from app.graph.finalize_node import make_finalize_node
from app.graph.general_answer_node import make_general_answer_node
from app.graph.generation_node import make_generation_node
from app.graph.intent_node import make_intent_gate_node
from app.graph.state import NL2SQLState
from app.graph.validation_node import make_validation_node
from app.graph.repair_node import REPAIRABLE_ERRORS, make_repair_node
from app.llm.client import LLMClient
from app.rag.retriever import SchemaRetrievalError, SchemaRetrievalRequest, SchemaRetriever
from app.schemas.domain import QueryIntent, QueryStatus, SchemaRetrieval, TraceEvent


def build_query_graph(
    *,
    database_executor: DatabaseExecutor,
    llm_client: LLMClient,
    schema_retriever: SchemaRetriever,
    access_policy: AccessPolicy,
    query_timeout_seconds: float,
    llm_timeout_seconds: float | None = None,
    intent_confidence_threshold: float = 0.75,
) -> Any:
    model_timeout_seconds = llm_timeout_seconds or query_timeout_seconds
    graph = StateGraph(NL2SQLState)
    graph.add_node("intent_gate", make_intent_gate_node(llm_client, model_timeout_seconds, intent_confidence_threshold))
    graph.add_node("retrieve_schema", _retrieve_schema_node(schema_retriever, access_policy))
    graph.add_node("generate_sql", make_generation_node(llm_client, model_timeout_seconds))
    graph.add_node("validate_sql", make_validation_node(access_policy))
    graph.add_node("execute_sql", make_execution_node(database_executor, access_policy, query_timeout_seconds))
    graph.add_node("repair_sql", make_repair_node(llm_client, model_timeout_seconds))
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
    graph.add_conditional_edges(
        "retrieve_schema",
        _route_after_retrieval,
        {"running": "generate_sql", "failed": "finalize", "blocked": "finalize"},
    )
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_edge("validate_sql", "execute_sql")
    graph.add_conditional_edges(
        "execute_sql",
        _route_after_execution,
        {"repair": "repair_sql", "finalize": "finalize"},
    )
    graph.add_edge("repair_sql", "validate_sql")
    graph.add_edge("general_answer", "finalize")
    graph.add_edge("clarify", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def _route_after_intent(state: NL2SQLState) -> str:
    intent = state.get("intent", QueryIntent.CLARIFICATION)
    return intent.value if isinstance(intent, QueryIntent) else str(intent)


def _route_after_retrieval(state: NL2SQLState) -> str:
    status = state.get("status", QueryStatus.FAILED)
    return status.value if isinstance(status, QueryStatus) else str(status)


def _route_after_execution(state: NL2SQLState) -> str:
    status = state.get("status", QueryStatus.FAILED)
    status_value = status.value if isinstance(status, QueryStatus) else str(status)
    category = state.get("error_category")
    category_value = category.value if hasattr(category, "value") else category
    if (
        status_value == QueryStatus.FAILED.value
        and category_value in REPAIRABLE_ERRORS
        and state.get("iteration", 0) < state.get("max_iterations", 0)
    ):
        return "repair"
    return "finalize"


def _retrieve_schema_node(retriever: SchemaRetriever, access_policy: AccessPolicy):
    def retrieve(state: NL2SQLState) -> dict[str, object]:
        request = SchemaRetrievalRequest(
            question=state["question"],
            database_id=state["database_id"],
            dialect=state["dialect"],
            allowed_tables=access_policy.allowed_tables,
            allowed_columns=access_policy.allowed_columns or {},
        )
        try:
            retrieval = retriever.retrieve(request)
        except SchemaRetrievalError as error:
            return {
                "status": QueryStatus.FAILED,
                "error_category": "schema_retrieval_error",
                "safe_error": "Schema 检索暂时不可用，请稍后重试。",
                "retrieval_mode": "error",
                "retrieved_tables": [],
                "trace": state.get("trace", [])
                + [TraceEvent(node="retrieve_schema", iteration=state["iteration"], error_category="schema_retrieval_error")],
            }
        except (DatabaseExecutionError, OSError, PermissionError, ValueError) as error:
            return {
                "status": QueryStatus.FAILED,
                "error_category": "schema_retrieval_error",
                "safe_error": "Schema 检索暂时不可用，请稍后重试。",
                "retrieval_mode": "error",
                "retrieved_tables": [],
                "trace": state.get("trace", [])
                + [TraceEvent(node="retrieve_schema", iteration=state["iteration"], error_category="schema_retrieval_error")],
            }
        except TypeError as error:
            # Keep P0 third-party/test retrievers compatible while migrating the contract.
            try:
                retrieval = retriever.retrieve(request.question, request.database_id)  # type: ignore[call-arg]
            except TypeError:
                raise error
        if not retrieval.documents:
            return {
                "status": QueryStatus.FAILED,
                "schema_version": retrieval.schema_version,
                "schema_context": [],
                "retrieval_mode": retrieval.retrieval_mode or "empty",
                "retrieval_scores": {},
                "retrieved_tables": [],
                "error_category": "schema_retrieval_error",
                "safe_error": "未检索到与问题匹配的授权 Schema，未执行 SQL。",
                "trace": state.get("trace", [])
                + [
                    TraceEvent(
                        node="retrieve_schema",
                        iteration=state["iteration"],
                        retrieved_document_count=0,
                        retrieval_mode=retrieval.retrieval_mode or "empty",
                        retrieved_tables=[],
                        error_category="schema_retrieval_error",
                    )
                ],
            }
        return {
            "schema_version": retrieval.schema_version,
            "schema_context": retrieval.documents,
            "retrieval_mode": retrieval.retrieval_mode or "full_schema",
            "retrieval_scores": retrieval.retrieval_scores,
            "retrieved_tables": [document.table_name for document in retrieval.documents],
            "trace": state.get("trace", [])
            + [
                TraceEvent(
                    node="retrieve_schema",
                    iteration=state["iteration"],
                    retrieved_document_count=len(retrieval.documents),
                    retrieval_mode=retrieval.retrieval_mode or "full_schema",
                    retrieved_tables=[document.table_name for document in retrieval.documents],
                )
            ],
        }

    return retrieve


class SQLiteSchemaRetriever:
    def __init__(self, database_executor: DatabaseExecutor) -> None:
        self.database_executor = database_executor

    def retrieve(self, request_or_question: SchemaRetrievalRequest | str, database_id: str | None = None):
        if isinstance(request_or_question, SchemaRetrievalRequest):
            request = request_or_question
            retrieval = self.database_executor.inspect_schema(request.database_id)
            return SchemaRetrieval(
                documents=_filter_documents(retrieval.documents, request),
                schema_version=retrieval.schema_version,
                retrieval_mode="full_schema",
            )
        return self.database_executor.inspect_schema(database_id or request_or_question)


def _filter_documents(documents, request: SchemaRetrievalRequest):
    allowed_tables = {name.lower() for name in request.allowed_tables}
    allowed_columns = {
        table.lower(): {column.lower() for column in columns}
        for table, columns in (request.allowed_columns or {}).items()
    }
    visible = []
    for document in documents:
        table_key = document.table_name.lower()
        if allowed_tables and table_key not in allowed_tables:
            continue
        if table_key in allowed_columns:
            columns = [column for column in document.column_names if column.lower() in allowed_columns[table_key]]
            content_lines = document.content.splitlines()
            column_line = next((line for line in content_lines if line.startswith("COLUMNS ")), "COLUMNS")
            parts = column_line.removeprefix("COLUMNS ").split(",")
            filtered_line = "COLUMNS " + ", ".join(
                part.strip() for part in parts if part.strip().split(" ", 1)[0] in columns
            )
            primary_key = next((line.removeprefix("PRIMARY KEY ") for line in content_lines if line.startswith("PRIMARY KEY ")), "")
            visible_primary = [item.strip() for item in primary_key.split(",") if item.strip() in columns]
            content = "\n".join(
                [
                    f"TABLE {document.table_name}",
                    filtered_line,
                    f"PRIMARY KEY {', '.join(visible_primary) if visible_primary else 'none'}",
                    "FOREIGN KEYS none",
                ]
            )
            visible.append(document.model_copy(update={"column_names": columns, "content": content}))
        else:
            visible.append(document)
    return visible
