"""Seed business knowledge documents that describe the demo SQLite database."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.knowledge.service import KnowledgeStore


DEFAULT_SOURCES = Path("data/knowledge_sources")
DEFAULT_DATABASE = Path("data/knowledge.sqlite3")
DEFAULT_ROOT = Path("data/knowledge")


def seed(database_path: Path, root: Path, source_root: Path) -> list[dict[str, object]]:
    """Replace only the canonical demo documents and make them readable to users."""

    store = KnowledgeStore(database_path, root, workers=1)
    try:
        sources = sorted(source_root.glob("*.md"))
        if not sources:
            raise FileNotFoundError(f"No Markdown sources found in {source_root}")
        by_name = {item["filename"]: item for item in store.list()}
        for source in sources:
            existing = by_name.get(source.name)
            if existing is not None:
                store.delete(existing["id"])
            created = store.create_upload(
                source.name,
                source.read_bytes(),
                "demo业务知识",
                "text/markdown",
            )
            indexed = _wait_for_indexed(store, str(created["id"]))
            store.set_acl(str(created["id"]), "all_authenticated")
            indexed["acl"] = store.get_acl(str(created["id"]))
        return [item for item in store.list() if item["filename"] in {source.name for source in sources}]
    finally:
        store.close()


def _wait_for_indexed(store: KnowledgeStore, document_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        document = store.get(document_id)
        if document and document["status"] == "indexed":
            return document
        if document and document["status"] == "failed":
            raise RuntimeError(document.get("failure_message") or "Knowledge indexing failed")
        time.sleep(0.05)
    raise TimeoutError(f"Knowledge document did not become indexed: {document_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    args = parser.parse_args()
    seeded = seed(args.database, args.root, args.sources)
    print(f"Seeded {len(seeded)} demo knowledge documents into {args.database}")


if __name__ == "__main__":
    main()
