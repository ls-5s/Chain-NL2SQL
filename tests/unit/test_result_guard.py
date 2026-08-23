from app.api.authorization import AccessPolicy
from app.db.result_guard import guard_query_result
from app.schemas.domain import QueryResult


def policy() -> AccessPolicy:
    return AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=frozenset({"users"}),
        allowed_columns={"users": frozenset({"id", "name", "email"})},
        masked_columns=frozenset({"users.email"}),
    )


def test_masks_sensitive_alias_and_expression() -> None:
    result = QueryResult(columns=["contact", "name"], rows=[["a@example.com", "Alice"]], row_count=1)
    guarded = guard_query_result(
        sql="SELECT email AS contact, name FROM users",
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=100,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert guarded.result.rows == [["***", "Alice"]]


def test_masks_sensitive_expression() -> None:
    result = QueryResult(columns=["contact"], rows=[["a@example.com"]], row_count=1)
    guarded = guard_query_result(
        sql="SELECT upper(email) AS contact FROM users",
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=100,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert guarded.result.rows == [["***"]]


def test_masks_sensitive_value_through_derived_alias() -> None:
    result = QueryResult(columns=["contact"], rows=[["a@example.com"]], row_count=1)
    guarded = guard_query_result(
        sql="SELECT contact FROM (SELECT email AS contact FROM users) AS source",
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=100,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert guarded.result.rows == [["***"]]


def test_rejects_unknown_result_shape() -> None:
    result = QueryResult(columns=["id", "name"], rows=[[1]], row_count=1)
    guarded = guard_query_result(
        sql="SELECT id, name FROM users",
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=100,
    )
    assert not guarded.allowed
    assert guarded.reason == "result_shape_mismatch"


def test_enforces_second_row_limit() -> None:
    result = QueryResult(columns=["id"], rows=[[1], [2]], row_count=2, truncated=False)
    guarded = guard_query_result(
        sql="SELECT id FROM users",
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=1,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert guarded.result.rows == [[1]]
    assert guarded.result.truncated is True
