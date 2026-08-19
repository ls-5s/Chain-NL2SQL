from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.authorization import local_access_policy
from app.api.dependencies import RequestContext, get_request_context
from app.api.response_mapper import map_query_state
from app.config.settings import Settings, get_settings
from app.db.sqlite_adapter import SQLiteAdapter
from app.graph.builder import SQLiteSchemaRetriever, build_query_graph
from app.graph.state import create_initial_state
from app.llm.factory import LLMConfigurationError, create_openai_client
from app.schemas.request import QueryRequest
from app.schemas.response import DatabaseListResponse, HealthResponse, QueryResponse

api_router = APIRouter(prefix="/api/v1", tags=["nl2sql"])
system_router = APIRouter(tags=["system"])


@system_router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(environment=settings.app_env)


@api_router.get("/databases", response_model=DatabaseListResponse)
def list_databases(settings: Settings = Depends(get_settings)) -> DatabaseListResponse:
    return DatabaseListResponse(database_ids=sorted(settings.allowed_database_ids))


@api_router.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest, context: RequestContext = Depends(get_request_context)) -> QueryResponse:
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
        state = create_initial_state(
            request_id=context.request_id,
            question=payload.question,
            database_id=payload.database_id,
            dialect="sqlite",
            max_iterations=payload.max_iterations or settings.max_iterations,
        )
        return map_query_state(await graph.ainvoke(state))
    except LLMConfigurationError as error:
        raise HTTPException(status_code=503, detail="LLM service is not configured.") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="The NL2SQL agent could not complete the query.") from error
    finally:
        database.close()
