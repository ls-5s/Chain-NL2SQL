from app.api.authorization import AccessPolicy
from app.db.result_guard import guard_query_result
from app.schemas.domain import QueryResult


def policy() -> AccessPolicy:
    return AccessPolicy(
        allowed_database_ids=frozenset({"demo"}),
        allowed_tables=frozenset({"用户"}),
        allowed_columns={"用户": frozenset({"编号", "用户名称", "邮箱"})},
        masked_columns=frozenset({"用户.邮箱"}),
    )


def test_masks_sensitive_alias_and_expression() -> None:
    result = QueryResult(columns=["联系方式", "用户名称"], rows=[["a@example.com", "用户0001"]], row_count=1)
    guarded = guard_query_result(
        sql='SELECT "邮箱" AS "联系方式", "用户名称" FROM "用户"',
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=100,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert guarded.result.rows == [["***", "用户0001"]]


def test_masks_sensitive_expression() -> None:
    result = QueryResult(columns=["联系方式"], rows=[["a@example.com"]], row_count=1)
    guarded = guard_query_result(
        sql='SELECT upper("邮箱") AS "联系方式" FROM "用户"',
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=100,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert guarded.result.rows == [["***"]]


def test_masks_sensitive_value_through_derived_alias() -> None:
    result = QueryResult(columns=["联系方式"], rows=[["a@example.com"]], row_count=1)
    guarded = guard_query_result(
        sql='SELECT "联系方式" FROM (SELECT "邮箱" AS "联系方式" FROM "用户") AS "来源"',
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=100,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert guarded.result.rows == [["***"]]


def test_rejects_unknown_result_shape() -> None:
    result = QueryResult(columns=["编号", "用户名称"], rows=[[1]], row_count=1)
    guarded = guard_query_result(
        sql='SELECT "编号", "用户名称" FROM "用户"',
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=100,
    )
    assert not guarded.allowed
    assert guarded.reason == "result_shape_mismatch"


def test_enforces_second_row_limit() -> None:
    result = QueryResult(columns=["编号"], rows=[[1], [2]], row_count=2, truncated=False)
    guarded = guard_query_result(
        sql='SELECT "编号" FROM "用户"',
        dialect="sqlite",
        result=result,
        access_policy=policy(),
        result_row_limit=1,
    )
    assert guarded.allowed
    assert guarded.result is not None
    assert guarded.result.rows == [[1]]
    assert guarded.result.truncated is True
