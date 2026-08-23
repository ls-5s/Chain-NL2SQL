"""Deterministic post-execution visibility checks for query results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import exp

from app.api.authorization import AccessPolicy
from app.schemas.domain import QueryResult


@dataclass(frozen=True)
class ResultGuardResult:
    allowed: bool
    result: QueryResult | None = None
    reason: str | None = None


def guard_query_result(
    *,
    sql: str,
    dialect: str,
    result: QueryResult | None,
    access_policy: AccessPolicy,
    result_row_limit: int,
) -> ResultGuardResult:
    """Validate shape and apply projection-aware masking without an LLM."""

    if result is None or result_row_limit <= 0:
        return ResultGuardResult(False, reason="result_missing")
    if result.row_count != len(result.rows):
        return ResultGuardResult(False, reason="result_row_count_mismatch")
    column_count = len(result.columns)
    if any(len(row) != column_count for row in result.rows):
        return ResultGuardResult(False, reason="result_shape_mismatch")

    try:
        statement = sqlglot.parse_one(sql, read=dialect or "sqlite")
    except sqlglot.errors.ParseError:
        return ResultGuardResult(False, reason="result_sql_parse_error")
    if not isinstance(statement, exp.Select):
        return ResultGuardResult(False, reason="result_sql_not_select")

    projections = statement.expressions
    if access_policy.allowed_columns and len(projections) != column_count:
        return ResultGuardResult(False, reason="result_projection_mismatch")
    if access_policy.allowed_columns and any(_is_projection_wildcard(item) for item in projections):
        return ResultGuardResult(False, reason="result_wildcard_not_allowed")

    sensitive_output_names = _collect_sensitive_output_names(statement, access_policy)
    masked_indexes = {
        index
        for index, projection in enumerate(projections)
        if index < column_count
        and _projection_contains_masked_column(
            projection, statement, access_policy, sensitive_output_names
        )
    }
    visible_rows = [list(row) for row in result.rows[:result_row_limit]]
    truncated = result.truncated or len(result.rows) > result_row_limit
    for row in visible_rows:
        for index in masked_indexes:
            row[index] = "***"
        # Keep the second boundary defensive if a custom executor returned a
        # value with a sensitive output name but no parseable projection.
        for index, column in enumerate(result.columns):
            if _is_masked_output_name(column, access_policy) and index < len(row):
                row[index] = "***"
    guarded = QueryResult(
        columns=list(result.columns),
        rows=visible_rows,
        row_count=len(visible_rows),
        truncated=truncated,
    )
    return ResultGuardResult(True, result=guarded)


def _is_projection_wildcard(projection: exp.Expression) -> bool:
    return isinstance(projection, exp.Star) or (isinstance(projection, exp.Column) and projection.is_star)


def _projection_contains_masked_column(
    projection: exp.Expression,
    statement: exp.Expression,
    access_policy: AccessPolicy,
    sensitive_output_names: set[str] | None = None,
) -> bool:
    columns = list(projection.find_all(exp.Column))
    if isinstance(projection, exp.Column):
        columns.append(projection)
    if not columns:
        return False
    tables = _table_aliases(statement)
    for column in columns:
        name = column.name.lower()
        if name in (sensitive_output_names or set()):
            return True
        table = column.table.lower() if column.table else ""
        resolved_table = tables.get(table, table)
        if _is_masked_name(name, resolved_table, access_policy):
            return True
        # Unqualified columns are conservatively masked if any visible source
        # table marks the same column as sensitive.
        if not table and any(_is_masked_name(name, source, access_policy) for source in tables.values()):
            return True
    return False


def _collect_sensitive_output_names(statement: exp.Expression, access_policy: AccessPolicy) -> set[str]:
    """Propagate sensitivity through derived tables and CTE output aliases."""

    names: set[str] = set()
    for select in statement.find_all(exp.Select):
        for projection in select.expressions:
            if _projection_contains_masked_column(projection, select, access_policy):
                output_name = getattr(projection, "alias_or_name", "")
                if output_name:
                    names.add(output_name.lower())
    return names


def _table_aliases(statement: exp.Expression) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for table in statement.find_all(exp.Table):
        name = table.name.lower()
        aliases[name] = name
        aliases[table.alias_or_name.lower()] = name
    return aliases


def _is_masked_name(column: str, table: str, access_policy: AccessPolicy) -> bool:
    masked = access_policy.masked_columns
    return column in masked or f"{table}.{column}" in masked


def _is_masked_output_name(column: str, access_policy: AccessPolicy) -> bool:
    normalized = column.lower()
    return normalized in {item.rsplit(".", 1)[-1] for item in access_policy.masked_columns}
