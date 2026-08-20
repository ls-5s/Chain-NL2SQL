from __future__ import annotations

import time

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutionError, DatabaseExecutor
from app.graph.state import NL2SQLState


def make_execution_node(database_executor: DatabaseExecutor, access_policy: AccessPolicy, timeout_seconds: float):
    def execute(state: NL2SQLState) -> dict[str, object]:
        if state["status"] != "running":
            return {}
        sql = state.get("validated_sql")
        if not sql:
            return {}
        expected_version = state.get("schema_version")
        if expected_version:
            get_schema_version = getattr(database_executor, "get_schema_version", None)
            if get_schema_version is not None:
                try:
                    current_version = get_schema_version(state["database_id"])
                except DatabaseExecutionError as error:
                    return {"status": "failed", "error_category": error.category, "safe_error": error.safe_message}
                if current_version != expected_version:
                    return {
                        "status": "failed",
                        "error_category": "schema_changed",
                        "safe_error": "The database schema changed during this request. Please retry.",
                    }
        try:
            result = database_executor.execute_readonly(sql, time.monotonic() + timeout_seconds, access_policy)
        except DatabaseExecutionError as error:
            return {"status": "failed", "error_category": error.category, "safe_error": error.safe_message}
        return {"query_result": result, "status": "succeeded"}

    return execute
