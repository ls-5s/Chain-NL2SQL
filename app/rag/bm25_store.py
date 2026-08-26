"""BM25 index construction and deterministic keyword retrieval."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.rag.retriever import SchemaRetrievalError
from app.schemas.domain import SchemaDocument


TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]", re.IGNORECASE)
TOKENIZER_VERSION = "aliases-v2"

# The SQLite demo has English identifiers but Chinese users.  Expanding both
# sides with the same aliases keeps the lexical fallback useful without
# pretending that arbitrary business synonyms can be inferred from the DB.
ALIAS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("users", "user", "用户", "客户", "customer", "customers"),
    ("orders", "order", "订单"),
    ("products", "product", "商品", "产品"),
    ("order_items", "order_item", "订单明细", "明细"),
    ("quantity", "数量", "个数", "多少", "count"),
    ("total_amount", "金额", "销售额", "总额", "amount", "revenue"),
    ("price", "价格", "单价", "price", "unit_price"),
    ("status", "状态", "status"),
    ("created_at", "时间", "日期", "created_at"),
    ("category", "类别", "分类", "category"),
    ("inventory", "库存", "存货", "可售库存"),
    ("warehouses", "warehouse", "仓库", "库房"),
    ("shipments", "shipment", "物流", "发货", "配送", "运单"),
    ("payments", "payment", "支付", "付款"),
    ("refunds", "refund", "退款", "退货款"),
    ("coupons", "coupon", "优惠券", "券"),
    ("promotions", "promotion", "促销", "活动"),
    ("returns", "return", "退货", "售后"),
    ("support_tickets", "ticket", "客服", "工单"),
    ("loyalty_accounts", "loyalty", "会员", "积分"),
)
TABLE_ALIAS_GROUPS = {
    "用户": ALIAS_GROUPS[0],
    "订单": ALIAS_GROUPS[1],
    "商品": ALIAS_GROUPS[2],
    "订单明细": ALIAS_GROUPS[3],
    "库存": ALIAS_GROUPS[10],
    "仓库": ALIAS_GROUPS[11],
    "物流单": ALIAS_GROUPS[12],
    "支付记录": ALIAS_GROUPS[13],
    "退款记录": ALIAS_GROUPS[14],
    "优惠券": ALIAS_GROUPS[15],
    "促销活动": ALIAS_GROUPS[16],
    "退货单": ALIAS_GROUPS[17],
    "客服工单": ALIAS_GROUPS[18],
    "会员积分账户": ALIAS_GROUPS[19],
}


def tokenize(text: str) -> list[str]:
    normalized = text.lower()
    tokens = TOKEN_PATTERN.findall(normalized)
    expanded = list(tokens)
    for group in ALIAS_GROUPS:
        if any(alias in normalized for alias in group):
            expanded.extend(group)
    return expanded


@dataclass(frozen=True)
class BM25Hit:
    document_id: str
    score: float


class BM25Store:
    """JSON-backed BM25 documents; the ranker is rebuilt on load."""

    def __init__(self, documents: list[SchemaDocument], tokens: list[list[str]]) -> None:
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as error:  # pragma: no cover - environment dependent
            raise SchemaRetrievalError("BM25 dependency is unavailable.") from error
        self.documents = documents
        self.tokens = tokens
        self._ranker = BM25Okapi(tokens)

    @classmethod
    def build(cls, path: str | Path, documents: Iterable[SchemaDocument]) -> "BM25Store":
        items = list(documents)
        tokens = [tokenize(f"{doc.table_name} {' '.join(doc.column_names)} {doc.content}") for doc in items]
        store = cls(items, tokens)
        store.save(path)
        return store

    @classmethod
    def load(cls, path: str | Path) -> "BM25Store":
        payload = json.loads((Path(path) / "bm25.json").read_text(encoding="utf-8"))
        if payload.get("tokenizer_version") != TOKENIZER_VERSION:
            raise SchemaRetrievalError("BM25 tokenizer version is incompatible.")
        documents = [SchemaDocument.model_validate(item) for item in payload["documents"]]
        return cls(documents, payload["tokens"])

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        (target / "bm25.json").write_text(
            json.dumps(
                {
                    "tokenizer_version": TOKENIZER_VERSION,
                    "documents": [doc.model_dump(mode="json") for doc in self.documents],
                    "tokens": self.tokens,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def query(self, question: str, top_k: int) -> list[BM25Hit]:
        if not self.documents or top_k <= 0:
            return []
        query_tokens = tokenize(question)
        normalized_question = question.lower()
        scores = self._ranker.get_scores(query_tokens)
        scored: list[tuple[int, float]] = []
        for index, score in enumerate(scores):
            overlap = len(set(query_tokens).intersection(self.tokens[index]))
            if overlap:
                # rank_bm25 can return zero for a unique term in a two-document corpus;
                # the tiny lexical tie-breaker keeps that deterministic and meaningful.
                adjusted = float(score) + overlap * 1e-6
                table_name = self.documents[index].table_name.lower()
                if table_name in TABLE_ALIAS_GROUPS and any(
                    alias in normalized_question for alias in TABLE_ALIAS_GROUPS[table_name]
                ):
                    # An explicit business object must outrank an unrelated
                    # metric field (e.g. quantity in order_items).
                    adjusted += 10.0
                scored.append((index, adjusted))
        ranked = sorted(scored, key=lambda item: (-item[1], self.documents[item[0]].table_name))
        return [BM25Hit(str(index), score) for index, score in ranked[:top_k]]
