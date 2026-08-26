"""Minimal LangGraph workflow for safe NL2SQL execution."""

from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import END, StateGraph

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutionError, DatabaseExecutor
from app.graph.execution_node import make_execution_node
from app.graph.finalize_node import make_finalize_node
from app.graph.clarification_node import make_clarification_node
from app.graph.general_answer_node import make_general_answer_node
from app.graph.grounded_answer_node import make_grounded_answer_node
from app.graph.generation_node import make_generation_node
from app.graph.intent_node import make_intent_gate_node
from app.graph.projection_review_node import make_projection_review_node
from app.graph.state import NL2SQLState
from app.graph.validation_node import make_validation_node
from app.graph.repair_node import REPAIRABLE_ERRORS, make_repair_node
from app.graph.result_guard_node import make_result_guard_node
from app.graph.result_summary_node import make_result_summary_node
from app.llm.client import LLMClient
from app.rag.retriever import SchemaRetrievalError, SchemaRetrievalRequest, SchemaRetriever
from app.schemas.domain import KnowledgeHit, QueryIntent, QueryStatus, SchemaRetrieval, TraceEvent


def build_query_graph(
    *,
    database_executor: DatabaseExecutor,
    llm_client: LLMClient,
    schema_retriever: SchemaRetriever,
    access_policy: AccessPolicy,
    query_timeout_seconds: float,
    llm_timeout_seconds: float | None = None,
    intent_confidence_threshold: float = 0.75,
    result_row_limit: int = 100,
    result_summary_enabled: bool = True,
    result_summary_max_chars: int = 12000,
    knowledge_retriever: Callable[[str, int], list[KnowledgeHit]] | None = None,
    knowledge_top_k: int = 5,
) -> Any:
    model_timeout_seconds = llm_timeout_seconds or query_timeout_seconds
    graph = StateGraph(NL2SQLState)
    graph.add_node("intent_gate", make_intent_gate_node(llm_client, model_timeout_seconds, intent_confidence_threshold))
    graph.add_node("retrieve_schema", _retrieve_schema_node(schema_retriever, access_policy))
    graph.add_node("generate_sql", make_generation_node(llm_client, model_timeout_seconds))
    graph.add_node("review_sql_projection", make_projection_review_node(llm_client, model_timeout_seconds))
    graph.add_node("validate_sql", make_validation_node(access_policy))
    graph.add_node("execute_sql", make_execution_node(database_executor, access_policy, query_timeout_seconds))
    graph.add_node("result_guard", make_result_guard_node(access_policy, result_row_limit))
    graph.add_node(
        "summarize_result",
        make_result_summary_node(
            llm_client,
            model_timeout_seconds,
            enabled=result_summary_enabled,
            max_chars=result_summary_max_chars,
        ),
    )
    graph.add_node("repair_sql", make_repair_node(llm_client, model_timeout_seconds))
    graph.add_node("general_answer", make_general_answer_node(llm_client, model_timeout_seconds))
    graph.add_node("retrieve_knowledge", _retrieve_knowledge_node(knowledge_retriever, knowledge_top_k))
    graph.add_node("grounded_answer", make_grounded_answer_node(llm_client, model_timeout_seconds))
    graph.add_node("finalize", make_finalize_node())
    graph.add_node("clarification_answer", make_clarification_node())
    # Knowledge retrieval is deliberately outside the V1 agent graph.  An
    # unprotected store must never influence routing or SQL generation.
    graph.set_entry_point("intent_gate")
    graph.add_conditional_edges(
        "intent_gate",
        _route_after_intent,
        {
            QueryIntent.DATA_QUERY.value: "retrieve_schema",
            QueryIntent.GENERAL_CHAT.value: "general_answer",
            "grounded_chat": "retrieve_knowledge",
            QueryIntent.CLARIFY.value: "clarification_answer",
            "needs_database": "clarification_answer",
        },
    )
    graph.add_conditional_edges(
        "retrieve_schema",
        _route_after_retrieval,
        {"running": "generate_sql", "failed": "finalize", "blocked": "finalize"},
    )
    graph.add_edge("generate_sql", "review_sql_projection")
    graph.add_conditional_edges(
        "review_sql_projection",
        _route_after_projection_review,
        {"validate": "validate_sql", "repair": "repair_sql", "finalize": "finalize"},
    )
    graph.add_edge("validate_sql", "execute_sql")
    graph.add_conditional_edges(
        "execute_sql",
        _route_after_execution,
        {"repair": "repair_sql", "result_guard": "result_guard", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "result_guard",
        _route_after_result_guard,
        {"summarize_result": "summarize_result", "finalize": "finalize"},
    )
    graph.add_edge("summarize_result", "finalize")
    graph.add_edge("repair_sql", "review_sql_projection")
    graph.add_edge("general_answer", "finalize")
    graph.add_edge("retrieve_knowledge", "grounded_answer")
    graph.add_edge("grounded_answer", "finalize")
    graph.add_edge("clarification_answer", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def _retrieve_knowledge_node(retriever: Callable[[str, int], list[KnowledgeHit]] | None, top_k: int):
    def retrieve(state: NL2SQLState) -> dict[str, object]:
        if retriever is None:
            return {"knowledge_hits": [], "knowledge_context": "", "knowledge_retrieval_error": "knowledge_unavailable"}
        try:
            # BM25/lexical retrieval can return weak matches for shared
            # Chinese stop characters.  Only pass materially relevant, ACL-
            # filtered evidence to the grounded-answer model; otherwise a
            # no-hit question could be answered from an unrelated document.
            hits = [hit for hit in retriever(state["question"], top_k) if hit.relevance >= 0.45]
            context = "\n\n".join(
                f"文档：{hit.title}\n分类：{hit.category}\n片段：{hit.excerpt}" for hit in hits
            )[:6000]
            return {"knowledge_hits": hits, "knowledge_context": context, "knowledge_retrieval_error": None}
        except Exception:
            # Knowledge retrieval is an enhancement; schema and general-answer paths remain available.
            return {
                "knowledge_hits": [],
                "knowledge_context": "",
                "knowledge_retrieval_error": "knowledge_retrieval_error",
            }

    return retrieve


def _route_after_intent(state: NL2SQLState) -> str:
    intent = state.get("intent", QueryIntent.GENERAL_CHAT)
    if intent == QueryIntent.DATA_QUERY and not state.get("database_id"):
        state["clarification_fields"] = ["数据库"]
        state["required_actions"] = ["select_database"]
        return "needs_database"
    if intent == QueryIntent.GENERAL_CHAT and state.get("knowledge_policy") == "required":
        return "grounded_chat"
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
    if status_value == QueryStatus.SUCCEEDED.value:
        return "result_guard"
    return "finalize"


def _route_after_projection_review(state: NL2SQLState) -> str:
    status = state.get("status", QueryStatus.FAILED)
    status_value = status.value if isinstance(status, QueryStatus) else str(status)
    category = state.get("error_category")
    category_value = category.value if hasattr(category, "value") else category
    if status_value == QueryStatus.RUNNING.value:
        return "validate"
    if (
        status_value == QueryStatus.FAILED.value
        and category_value in REPAIRABLE_ERRORS
        and state.get("iteration", 0) < state.get("max_iterations", 0)
    ):
        return "repair"
    return "finalize"


def _route_after_result_guard(state: NL2SQLState) -> str:
    status = state.get("status", QueryStatus.FAILED)
    status_value = status.value if isinstance(status, QueryStatus) else str(status)
    return "summarize_result" if status_value == QueryStatus.SUCCEEDED.value else "finalize"


def _retrieve_schema_node(retriever: SchemaRetriever, access_policy: AccessPolicy):
    def retrieve(state: NL2SQLState) -> dict[str, object]:
        if not state.get("database_id"):
            return {"status": QueryStatus.NEEDS_CLARIFICATION, "required_actions": ["select_database"]}
        database_policy = access_policy.for_database(state["database_id"])
        request = SchemaRetrievalRequest(
            question=state["question"],
            database_id=state["database_id"],
            dialect=state["dialect"],
            allowed_tables=database_policy.allowed_tables,
            allowed_columns=database_policy.allowed_columns or {},
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
        # An empty allowlist is an explicit deny-all scope for registered databases.
        if table_key not in allowed_tables:
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
