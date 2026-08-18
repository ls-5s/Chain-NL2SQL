"""将 SQLite 元数据标准化为与方言无关的模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedColumn:
    # SchemaDocument 和访问策略使用的标准字段名。
    name: str
    # 保留源数据库类型，供模型上下文使用。
    data_type: str
    # SQLite 允许该字段为空时为 True。
    nullable: bool
    # SQLite 对非主键使用 0，对主键使用主键位置编号。
    primary_key_position: int


@dataclass(frozen=True)
class NormalizedForeignKey:
    # 关系中的本地字段。
    column: str
    # 目标关系中的引用表和引用字段。
    referenced_table: str
    referenced_column: str


@dataclass(frozen=True)
class NormalizedTable:
    # 稳定的表名和标准化关系元数据。
    name: str
    columns: tuple[NormalizedColumn, ...]
    foreign_keys: tuple[NormalizedForeignKey, ...]
