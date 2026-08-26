"""Materialize a deterministic BM25 Schema-RAG index for the demo database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.sqlite_adapter import SQLiteAdapter
from app.rag.index_manager import SchemaIndexManager
from app.rag.retriever import SchemaRetrievalRequest


def build(database: Path, index_root: Path, database_id: str = "demo") -> dict[str, object]:
    """Build the index from every table and column actually present in SQLite."""
    adapter = SQLiteAdapter(database_id, str(database))
    schema = adapter.inspect_schema(database_id)
    tables = frozenset(document.table_name for document in schema.documents)
    manager = SchemaIndexManager(
        adapter.inspect_schema,
        root=index_root,
        mode="bm25",
        fallback_mode="bm25",
        top_k=5,
    )
    result = manager.retrieve(
        SchemaRetrievalRequest(
            question="用户 商品 订单 支付 库存 物流 优惠 售后 会员",
            database_id=database_id,
            dialect="sqlite",
            allowed_tables=tables,
            # Omitting per-table entries authorizes every current column.
            allowed_columns={},
        )
    )
    return {
        "schema_version": result.schema_version,
        "retrieval_mode": result.retrieval_mode,
        "indexed_table_count": len(tables),
        "retrieved_tables": [document.table_name for document in result.documents],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=Path("data/demo.sqlite"))
    parser.add_argument("--index-root", type=Path, default=Path("data/schema_metadata_runtime"))
    args = parser.parse_args()
    print(build(args.database, args.index_root))


if __name__ == "__main__":
    main()
