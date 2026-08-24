"""Materialize the deterministic BM25 Schema-RAG index for the demo database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.sqlite_adapter import SQLiteAdapter
from app.rag.index_manager import SchemaIndexManager
from app.rag.retriever import SchemaRetrievalRequest


TABLES = frozenset({"users", "products", "orders", "order_items"})
COLUMNS = {
    "users": frozenset({"id", "name", "email", "created_at"}),
    "products": frozenset({"id", "name", "category", "price"}),
    "orders": frozenset({"id", "user_id", "status", "total_amount", "created_at"}),
    "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
}


def build(database: Path, index_root: Path, database_id: str = "demo") -> dict[str, object]:
    adapter = SQLiteAdapter(database_id, str(database))
    manager = SchemaIndexManager(
        adapter.inspect_schema,
        root=index_root,
        mode="bm25",
        fallback_mode="bm25",
        top_k=5,
    )
    result = manager.retrieve(
        SchemaRetrievalRequest(
            question="用户订单商品销售额数量金额",
            database_id=database_id,
            dialect="sqlite",
            allowed_tables=TABLES,
            allowed_columns=COLUMNS,
        )
    )
    return {
        "schema_version": result.schema_version,
        "retrieval_mode": result.retrieval_mode,
        "tables": [document.table_name for document in result.documents],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=Path("data/demo.sqlite"))
    parser.add_argument("--index-root", type=Path, default=Path("data/schema_metadata_runtime"))
    args = parser.parse_args()
    print(build(args.database, args.index_root))


if __name__ == "__main__":
    main()
