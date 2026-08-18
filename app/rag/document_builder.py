"""根据标准化元数据构建稳定的 SchemaDocument。"""

from __future__ import annotations

import hashlib

from app.rag.normalizer import NormalizedTable
from app.schemas.domain import SchemaDocument, SchemaRetrieval


def build_schema_retrieval(
    database_id: str, tables: tuple[NormalizedTable, ...]
) -> SchemaRetrieval:
    # 保留 introspector 的确定性表顺序，确保检索结果稳定。
    documents: list[SchemaDocument] = []
    for table in tables:
        # 以紧凑、适合模型读取的格式渲染字段类型和可空性。
        columns = ", ".join(
            f"{column.name} {column.data_type or 'UNKNOWN'}"
            f" {'NULL' if column.nullable else 'NOT NULL'}"
            for column in table.columns
        )
        # 保留 SQLite 元数据中的复合主键顺序。
        primary_keys = [
            column.name
            for column in table.columns
            if column.primary_key_position > 0
        ]
        # 将关系渲染为 local_column->remote_table.remote_column。
        foreign_keys = [
            f"{key.column}->{key.referenced_table}.{key.referenced_column}"
            for key in table.foreign_keys
        ]
        # 这段稳定文本同时作为 Prompt 上下文和版本计算内容。
        content = "\n".join(
            [
                f"TABLE {table.name}",
                f"COLUMNS {columns}",
                f"PRIMARY KEY {', '.join(primary_keys) if primary_keys else 'none'}",
                f"FOREIGN KEYS {', '.join(foreign_keys) if foreign_keys else 'none'}",
            ]
        )
        # 保留结构化字段，供策略和检索过滤使用。
        documents.append(
            SchemaDocument(
                table_name=table.name,
                content=content,
                database_id=database_id,
                column_names=[column.name for column in table.columns],
            )
        )

    # 只对规范化 Schema 文本哈希，使相同 Schema 产生相同版本。
    canonical = "\n\n".join(document.content for document in documents)
    schema_version = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    # 返回供后续 Graph 检索节点使用的稳定契约。
    return SchemaRetrieval(documents=documents, schema_version=schema_version)
