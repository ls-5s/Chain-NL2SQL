from __future__ import annotations

from app.api.authorization import AccessPolicy
from app.db.security_policy import validate_readonly_sql
from app.graph.state import NL2SQLState


def make_validation_node(access_policy: AccessPolicy):
    def validate(state: NL2SQLState) -> dict[str, object]:
        if state["status"] != "running":
            return {}
        sql = state.get("generated_sql")
        if not sql:
            return {"status": "failed", "error_category": "invalid_model_output", "safe_error": "No SQL was generated."}
        # API payloads may omit bindings (or normalize them to null).  The
        # security validator expects a concrete parameter-name set and must
        # fail closed without raising a TypeError at the SSE boundary.
        bound_parameters = state.get("bound_parameters") or {}
        result = validate_readonly_sql(
            sql,
            state["dialect"],
            access_policy.for_database(state["database_id"]),
            set(bound_parameters),
        )
        if not result.allowed:
            category = "syntax_error" if result.reason == "syntax_error" else "unsafe_sql"
            status = "failed" if category == "syntax_error" else "blocked"
            return {"status": status, "error_category": category, "safe_error": "The generated SQL was blocked by the read-only security policy."}
        return {"validated_sql": sql}

    return validate
