from concurrent.futures import ThreadPoolExecutor

from app.conversations.repository import ConversationRepository
from app.schemas.domain import QueryIntent, QueryResult, QueryStatus
from app.schemas.response import QueryResponse


def response() -> QueryResponse:
    return QueryResponse(
        request_id="request-1",
        intent=QueryIntent.DATA_QUERY,
        status=QueryStatus.SUCCEEDED,
        iteration=1,
        final_answer="查询完成。",
        result=QueryResult(columns=["id", "name"], rows=[[7, "Ada"]], row_count=1),
        generated_sql="SELECT id, name FROM users ORDER BY id",
    )


def test_persists_turn_context_reference_and_cascade_delete(tmp_path) -> None:
    repository = ConversationRepository(
        tmp_path / "conversations.sqlite3",
        primary_key_resolver=lambda database_id, table: ("id",) if (database_id, table) == ("demo", "users") else (),
    )
    first = repository.create_conversation("single-user", "demo")
    second = repository.create_conversation("single-user", "demo")

    first_turn = repository.start_turn("single-user", first["id"], "查询用户", "会话数据源：demo")
    repository.append_progress(first_turn["assistant_message_id"], {"node": "generate_sql", "message": "生成 SQL"})
    repository.finish_turn(first_turn["turn_id"], first_turn["assistant_message_id"], response())

    detail = repository.get_conversation("single-user", first["id"])
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][-1]["progress"][0]["node"] == "generate_sql"

    context, bindings = repository.build_context("single-user", first["id"], "继续查用户", 6000)
    assert "查询用户" in context
    assert bindings == {}
    other_context, _ = repository.build_context("single-user", second["id"], "继续查用户", 6000)
    assert "查询用户" not in other_context

    reference = repository.create_result_reference("single-user", first["id"], first_turn["turn_id"], 0)
    _, bindings = repository.build_context("single-user", first["id"], "查看该用户", 6000, [reference["id"]])
    assert bindings == {"selected_users_id": 7}

    repository.delete_conversation("single-user", first["id"])
    assert [item["id"] for item in repository.list_conversations("single-user")] == [second["id"]]


def test_context_uses_fts_and_turn_creation_is_concurrent_safe(tmp_path) -> None:
    repository = ConversationRepository(tmp_path / "conversations.sqlite3")
    conversation = repository.create_conversation("single-user", "demo")

    for question in ["查看订单状态", "查询商品销量", "订单状态按天统计"]:
        turn = repository.start_turn("single-user", conversation["id"], question, "")
        repository.finish_turn(turn["turn_id"], turn["assistant_message_id"], response())

    context, _ = repository.build_context("single-user", conversation["id"], "继续按订单状态查询", 220)
    assert len(context) <= 220
    assert "订单状态" in context

    def start(index: int) -> str:
        turn = repository.start_turn("single-user", conversation["id"], f"并发查询 {index}", "")
        return turn["turn_id"]

    with ThreadPoolExecutor(max_workers=4) as executor:
        turn_ids = list(executor.map(start, range(4)))
    assert len(set(turn_ids)) == 4


def test_repository_recovers_running_turns_on_initialization(tmp_path) -> None:
    path = tmp_path / "conversations.sqlite3"
    repository = ConversationRepository(path)
    conversation = repository.create_conversation("single-user", "demo")
    turn = repository.start_turn("single-user", conversation["id"], "查询用户", "")

    recovered = ConversationRepository(path)
    detail = recovered.get_conversation("single-user", conversation["id"])

    assert detail["messages"][-1]["status"] == "failed"
    assert detail["messages"][-1]["content"] == "上一次查询因服务中断未完成，请重试。"
    with recovered._connection() as connection:
        status = connection.execute("SELECT status FROM conversation_turns WHERE id = ?", (turn["turn_id"],)).fetchone()[0]
    assert status == "failed"
