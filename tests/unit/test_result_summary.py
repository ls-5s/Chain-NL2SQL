import json

from app.graph.result_summary_node import _fallback, _serialize_result
from app.api.response_mapper import map_query_state
from app.graph.intent_node import _is_database_follow_up
from app.schemas.domain import QueryIntent, QueryResult, QueryStatus


def test_summary_question_is_not_treated_as_recommendation() -> None:
    result = QueryResult(
        columns=["id", "title", "content"],
        rows=[[1, "第一篇", "<p>第一篇内容</p>"], [2, "第二篇", "<p>第二篇内容</p>"]],
        row_count=2,
    )

    answer = _fallback(result, "总结每一篇文章是写的什么")

    assert "推荐这篇" not in answer
    assert "第一篇" in answer
    assert "第二篇" in answer


def test_long_result_is_compacted_as_valid_json_for_summary() -> None:
    result = QueryResult(
        columns=["id", "title", "content"],
        rows=[[index, f"文章 {index}", "正文" * 2_000] for index in range(12)],
        row_count=12,
    )

    payload = json.loads(_serialize_result(result, 12_000))

    assert len(payload["rows"]) == 12
    assert len(json.dumps(payload, ensure_ascii=False)) <= 12_000


def test_wide_result_keeps_real_values_when_sampling_for_summary() -> None:
    result = QueryResult(
        columns=[f"column_{index}" for index in range(18)],
        rows=[[f"value-{row}-{column}" for column in range(18)] for row in range(100)],
        row_count=100,
        truncated=True,
    )

    payload = json.loads(_serialize_result(result, 12_000))

    assert len(payload["rows"]) < 100
    assert payload["rows"][0][0] == "value-0-0"
    assert payload["rows_omitted"] > 0


def test_truncated_result_uses_deterministic_summary() -> None:
    class UnexpectedLLM:
        def generate(self, *args, **kwargs):
            raise AssertionError("truncated results must not be sent to the summarizer")

    from app.graph.result_summary_node import make_result_summary_node

    summarize = make_result_summary_node(UnexpectedLLM(), timeout_seconds=1, enabled=True)
    state = summarize(
        {
            "status": QueryStatus.SUCCEEDED,
            "iteration": 1,
            "question": "查询有哪些商品",
            "query_result": QueryResult(
                columns=["商品名称"], rows=[["显示器 0001"]], row_count=100, truncated=True
            ),
            "trace": [],
        }
    )

    assert state["answer_source"] == "deterministic_fallback"
    assert "100" in state["final_answer"]
    assert "截断" in state["final_answer"]


def test_summary_response_does_not_expose_raw_result_rows() -> None:
    response = map_query_state(
        {
            "request_id": "request-1",
            "question": "总结每一篇文章是写的什么",
            "intent": QueryIntent.DATA_QUERY,
            "status": QueryStatus.SUCCEEDED,
            "iteration": 1,
            "final_answer": "各篇文章摘要：...",
            "query_result": QueryResult(columns=["title"], rows=[["第一篇"]], row_count=1),
            "trace": [],
        }
    )

    assert response.result is None


def test_article_content_follow_up_keeps_the_selected_record_context() -> None:
    context = "历史回合：推荐这篇：面试官：说说JavaScript中的数据类型？存储上的差别？\n涉及表：articles"

    assert _is_database_follow_up("有哪些内容", context)
    assert not _is_database_follow_up("为什么是这个", context)
