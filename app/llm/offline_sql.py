"""Strict local fallback for unambiguous read-only requests."""

from __future__ import annotations

from collections.abc import Iterable

from app.schemas.domain import SchemaDocument

_TABLE_ALIASES = {
    "products": ("商品", "产品", "product", "products"),
    "users": ("用户", "客户", "user", "users"),
    "orders": ("订单", "order", "orders"),
    "order_items": ("订单明细", "明细", "order item", "order_items"),
}
_COLUMN_ALIASES = {
    "name": ("名称", "名字", "name"),
    "price": ("价格", "单价", "price"),
    "category": ("类别", "分类", "category"),
    "status": ("状态", "status"),
    "total_amount": ("金额", "总额", "销售额", "total amount"),
    "quantity": ("数量", "quantity"),
    "created_at": ("时间", "日期", "created at"),
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
        return f"SELECT COUNT(*) AS count FROM {document.table_name}"
    selected = [
        columns[column]
        for column, aliases in _COLUMN_ALIASES.items()
        if column in columns and any(alias in normalized for alias in aliases)
    ]
    if not selected:
        return None
    if document.table_name.lower() == "products" and selected == [columns.get("price")] and "name" in columns:
        selected.insert(0, columns["name"])
    order_by = f" ORDER BY {columns['id']}" if "id" in columns else ""
    return f"SELECT {', '.join(selected)} FROM {document.table_name}{order_by}"


def _matching_document(question: str, documents: Iterable[SchemaDocument]) -> SchemaDocument | None:
    matches = [
        document
        for document in documents
        if any(alias in question for alias in _TABLE_ALIASES.get(document.table_name.lower(), (document.table_name.lower(),)))
    ]
    return matches[0] if len(matches) == 1 else None
