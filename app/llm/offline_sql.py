"""Strict local fallback for unambiguous read-only requests."""

from __future__ import annotations

from collections.abc import Iterable

from app.schemas.domain import SchemaDocument

_TABLE_ALIASES = {
    "商品": ("商品", "产品"),
    "用户": ("用户", "客户"),
    "订单": ("订单",),
    "订单明细": ("订单明细", "明细"),
}
_COLUMN_ALIASES = {
    "商品名称": ("名称", "名字", "商品"),
    "销售价": ("价格", "单价", "售价"),
    "分类编号": ("类别", "分类"),
    "订单状态": ("状态",),
    "实付金额": ("金额", "总额", "销售额"),
    "数量": ("数量",),
    "创建时间": ("时间", "日期"),
}


def generate_offline_sql(question: str, documents: Iterable[SchemaDocument], dialect: str) -> str | None:
    if dialect not in {"sqlite", "mysql"}:
        return None
    normalized = question.lower()
    document = _matching_document(normalized, documents)
    if document is None:
        return None
    columns = {column.lower(): column for column in document.column_names}
    if any(term in normalized for term in ("多少", "几条", "数量", "count")):
        return f'SELECT COUNT(*) AS "数量" FROM "{document.table_name}"'
    selected = [
        columns[column]
        for column, aliases in _COLUMN_ALIASES.items()
        if column in columns and any(alias in normalized for alias in aliases)
    ]
    if not selected:
        return None
    if document.table_name == "商品" and selected == [columns.get("销售价")] and "商品名称" in columns:
        selected.insert(0, columns["商品名称"])
    quoted = [f'"{column}"' for column in selected]
    order_by = f' ORDER BY "{columns["编号"]}"' if "编号" in columns else ""
    return f'SELECT {", ".join(quoted)} FROM "{document.table_name}"{order_by}'


def _matching_document(question: str, documents: Iterable[SchemaDocument]) -> SchemaDocument | None:
    matches = [
        document
        for document in documents
        if any(alias in question for alias in _TABLE_ALIASES.get(document.table_name.lower(), (document.table_name.lower(),)))
    ]
    return matches[0] if len(matches) == 1 else None
