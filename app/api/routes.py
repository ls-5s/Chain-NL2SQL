from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import RequestContext, get_request_context
from app.api.response_mapper import map_query_state
from app.config.settings import Settings, get_settings
from app.db.sqlite_adapter import SQLiteAdapter
from app.graph.builder import SQLiteSchemaRetriever, build_query_graph
from app.graph.state import NL2SQLState, create_initial_state
from app.llm.factory import LLMConfigurationError, create_openai_client
from app.schemas.request import QueryRequest
from app.schemas.response import DatabaseListResponse, HealthResponse

api_router = APIRouter(prefix="/api/v1", tags=["nl2sql"])
system_router = APIRouter(tags=["system"])


@system_router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(environment=settings.app_env)


@api_router.get("/databases", response_model=DatabaseListResponse)
def list_databases(settings: Settings = Depends(get_settings)) -> DatabaseListResponse:
    return DatabaseListResponse(database_ids=sorted(settings.allowed_database_ids))


@api_router.post("/query")
async def query(
    payload: QueryRequest,
    context: RequestContext = Depends(get_request_context),
) -> StreamingResponse:
    settings = get_settings()
    if payload.database_id not in context.access_policy.allowed_database_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Database is not allowed.")
    if payload.database_id != "demo":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database adapter is not configured.")

    database = SQLiteAdapter(payload.database_id, settings.demo_database_path, settings.result_row_limit)
    try:
        llm_client = create_openai_client(settings)
        graph = build_query_graph(
            database_executor=database,
            llm_client=llm_client,
            schema_retriever=SQLiteSchemaRetriever(database),
            access_policy=context.access_policy,
            query_timeout_seconds=settings.query_timeout_seconds,
        )
    except LLMConfigurationError as error:
        database.close()
        raise HTTPException(status_code=503, detail="LLM service is not configured.") from error
    except ValueError as error:
        database.close()
        raise HTTPException(status_code=400, detail=str(error)) from error

    state = create_initial_state(
        request_id=context.request_id,
        question=payload.question,
        database_id=payload.database_id,
        dialect="sqlite",
        max_iterations=payload.max_iterations or settings.max_iterations,
    )
    return StreamingResponse(
        _stream_graph(graph, state, database),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_graph(graph: Any, state: NL2SQLState, database: SQLiteAdapter) -> AsyncIterator[str]:
    current_state: dict[str, Any] = dict(state)
    try:
        yield _sse("start", {"request_id": state["request_id"]})
        async for update in graph.astream(state, stream_mode="updates"):
            for node, node_update in update.items():
                current_state.update(node_update)
                progress: dict[str, Any] = {
                    "request_id": state["request_id"],
                    "node": node,
                    "status": _json_value(current_state.get("status", "running")),
                    "iteration": current_state.get("iteration", 0),
                    "message": _node_message(node),
                    "explanation": _node_explanation(node, current_state),
                }
                if node == "retrieve_schema":
                    progress["retrieved_document_count"] = len(current_state.get("schema_context", []))
                if current_state.get("error_category"):
                    progress["error_category"] = _json_value(current_state["error_category"])
                if node == "retrieve_schema":
                    progress["tables"] = [
                        document.table_name for document in current_state.get("schema_context", [])
                    ]
                if node == "generate_sql" and current_state.get("generated_sql"):
                    progress["sql"] = current_state["generated_sql"]
                if node == "validate_sql":
                    progress["validated"] = bool(current_state.get("validated_sql"))
                if node == "execute_sql" and current_state.get("query_result"):
                    progress["row_count"] = current_state["query_result"].row_count
                yield _sse("progress", progress)

        response = map_query_state(current_state)
        yield _sse("complete", response.model_dump(mode="json"))
    except LLMConfigurationError:
        yield _sse("error", {"status_code": 503, "detail": "LLM service is not configured."})
    except Exception:
        yield _sse("error", {"status_code": 502, "detail": "The NL2SQL agent could not complete the query."})
    finally:
        database.close()


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _json_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _node_message(node: str) -> str:
    return {
        "retrieve_schema": "正在读取数据库 Schema",
        "generate_sql": "正在生成只读 SQL",
        "validate_sql": "正在校验 SQL 安全性",
        "execute_sql": "正在执行查询",
        "finalize": "正在整理查询结果",
    }.get(node, "正在处理查询")


def _node_explanation(node: str, state: dict[str, Any]) -> str:
    if node == "retrieve_schema":
        count = len(state.get("schema_context", []))
        return f"读取服务端允许访问的 Schema，共获得 {count} 张表的结构信息。"
    if node == "generate_sql":
        return "根据用户问题和固定 Schema 生成单条只读 SQL。"
    if node == "validate_sql":
        if state.get("validated_sql"):
            return "SQL 已通过单语句、只读操作、表白名单和字段白名单校验。"
        return "SQL 未通过安全校验，已阻止执行。"
    if node == "execute_sql":
        result = state.get("query_result")
        if result:
            return f"在超时和结果行数限制内执行 SQL，返回 {result.row_count} 行。"
        return "执行已验证的只读 SQL。"
    if node == "finalize":
        return "整理安全响应，不向客户端暴露原始异常或连接信息。"
    return "执行查询工作流。"
