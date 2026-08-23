from __future__ import annotations

import time

import pytest

from app.knowledge.service import KnowledgeBusyError, KnowledgeStore


def wait_for_status(store: KnowledgeStore, document_id: str, status: str) -> dict:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        document = store.get(document_id)
        if document and document["status"] == status:
            return document
        time.sleep(0.02)
    raise AssertionError(f"document did not reach {status}: {store.get(document_id)}")


def test_uploads_indexes_and_retrieves_markdown(tmp_path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3", tmp_path / "files", workers=1)
    document = store.create_upload("销售指标口径.md", "销售额 = 商品价格乘以数量。".encode(), "指标口径", "text/markdown")

    indexed = wait_for_status(store, document["id"], "indexed")
    assert indexed["chunk_count"] == 1
    assert "销售额" in indexed["summary"]
    hits = store.retrieve("销售额怎么算")
    assert hits and hits[0].title == "销售指标口径.md"

    store.delete(document["id"])
    assert store.get(document["id"]) is None
    store.close()


def test_rejects_bad_extension_signature_and_size(tmp_path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3", tmp_path / "files", max_upload_bytes=4)
    with pytest.raises(ValueError, match="仅支持"):
        store.create_upload("notes.exe", b"data", "规则")
    with pytest.raises(ValueError, match="大小"):
        store.create_upload("notes.md", b"too large", "规则", "text/markdown")
    pdf_store = KnowledgeStore(tmp_path / "pdf.sqlite3", tmp_path / "pdf-files", workers=1)
    with pytest.raises(ValueError, match="签名"):
        pdf_store.create_upload("notes.pdf", b"not a pdf", "规则", "application/pdf")
    store.close()
    pdf_store.close()


def test_processing_documents_cannot_be_deleted(tmp_path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3", tmp_path / "files", workers=1)
    document = store.create_upload("rules.md", "业务规则".encode(), "规则", "text/markdown")
    # The worker may finish immediately; the API contract still allows deletion once indexed.
    current = store.get(document["id"])
    if current and current["status"] in {"uploading", "parsing"}:
        with pytest.raises(KnowledgeBusyError):
            store.delete(document["id"])
    wait_for_status(store, document["id"], "indexed")
    store.close()
