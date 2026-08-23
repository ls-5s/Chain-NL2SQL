import sqlite3
import time

from app.graph.grounded_answer_node import make_grounded_answer_node
from app.knowledge.service import KnowledgeStore
from app.schemas.domain import KnowledgeHit, QueryStatus
from tests.fakes.fake_llm import FakeLLM


def wait_indexed(store: KnowledgeStore, document_id: str) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if store.get(document_id)["status"] == "indexed":
            return
        time.sleep(0.02)
    raise AssertionError(store.get(document_id))


def test_acl_is_deny_by_default_and_revoke_is_immediate(tmp_path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3", tmp_path / "files", workers=1)
    document = store.create_upload("policy.md", "审批流程必须留痕。".encode(), "制度", "text/markdown")
    wait_indexed(store, document["id"])
    assert store.retrieve("审批流程", user_id="member", role="member") == []
    store.set_acl(document["id"], "all_authenticated")
    assert store.retrieve("审批流程", user_id="member", role="member")
    store.set_acl(document["id"], "deny")
    assert store.retrieve("审批流程", user_id="member", role="member") == []
    store.close()


def test_role_and_user_acl_do_not_leak_to_other_principal(tmp_path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3", tmp_path / "files", workers=1)
    document = store.create_upload("secret.md", "财务审批阈值为十万元。".encode(), "制度", "text/markdown")
    wait_indexed(store, document["id"])
    store.set_acl(document["id"], "role", role="finance")
    assert store.retrieve("审批阈值", user_id="u1", role="finance")
    assert store.retrieve("审批阈值", user_id="u2", role="member") == []
    store.set_acl(document["id"], "user", user_id="u1")
    assert store.retrieve("审批阈值", user_id="u1", role="member")
    assert store.retrieve("审批阈值", user_id="u2", role="finance") == []
    store.close()


def test_reindex_failure_keeps_existing_index(tmp_path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3", tmp_path / "files", workers=1)
    document = store.create_upload("stable.md", "稳定索引内容。".encode(), "制度", "text/markdown")
    wait_indexed(store, document["id"])
    with sqlite3.connect(store.database_path) as connection:
        connection.execute(
            "UPDATE knowledge_jobs SET status = 'running', attempts = 3 WHERE document_id = ?",
            (document["id"],),
        )
        job_id = connection.execute("SELECT id FROM knowledge_jobs WHERE document_id = ?", (document["id"],)).fetchone()[0]
    store._fail_job(job_id, "rebuild failed")
    assert store.get(document["id"])["status"] == "indexed"
    assert store.retrieve("稳定索引", user_id=None)
    store.close()


def test_grounded_answer_rejects_missing_or_invalid_citation() -> None:
    node = make_grounded_answer_node(FakeLLM(["没有引用的回答"]), 1)
    state = {
        "question": "制度是什么",
        "knowledge_hits": [KnowledgeHit(document_id="doc-1", title="policy", category="制度", excerpt="必须留痕", relevance=0.9)],
    }
    result = node(state)
    assert result["status"] == QueryStatus.NO_GROUNDED_ANSWER
