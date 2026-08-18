"""读取 SQLite 表、字段和关系。"""

from __future__ import annotations

import sqlite3

from app.rag.document_builder import build_schema_retrieval
from app.rag.normalizer import (
    NormalizedColumn,
    NormalizedForeignKey,
    NormalizedTable,
)
from app.schemas.domain import SchemaRetrieval


def _quote_identifier(identifier: str) -> str:
    # 在 PRAGMA 语句中使用元数据标识符前先进行引用和转义。
    return '"' + identifier.replace('"', '""') + '"'


def inspect_sqlite_schema(connection: sqlite3.Connection, database_id: str) -> SchemaRetrieval:
    # 排除 SQLite 内部表并按名称排序，保证版本哈希稳定。
    table_rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    tables: list[NormalizedTable] = []
    for (table_name,) in table_rows:
        # PRAGMA table_info 返回字段名、类型、可空性和主键位置。
        columns = tuple(
            NormalizedColumn(
                name=row[1],
                data_type=row[2] or "",
                nullable=not bool(row[3]),
                primary_key_position=int(row[5]),
            )
            for row in connection.execute(f"PRAGMA table_info({_quote_identifier(table_name)})")
        )
        # PRAGMA foreign_key_list 返回本地字段和引用字段名称。
        foreign_keys = tuple(
            NormalizedForeignKey(
                column=row[3],
                referenced_table=row[2],
                referenced_column=row[4],
            )
            for row in connection.execute(f"PRAGMA foreign_key_list({_quote_identifier(table_name)})")
        )
        # 将驱动返回的行转换为与方言无关的领域元数据。
        tables.append(
            NormalizedTable(
                name=table_name,
                columns=columns,
                foreign_keys=foreign_keys,
            )
        )
    # 由 document_builder 计算规范化内容和 Schema 版本。
    return build_schema_retrieval(database_id, tuple(tables))
