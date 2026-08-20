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


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


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
        documents = [SchemaDocument.model_validate(item) for item in payload["documents"]]
        return cls(documents, payload["tokens"])

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        (target / "bm25.json").write_text(
            json.dumps(
                {"documents": [doc.model_dump(mode="json") for doc in self.documents], "tokens": self.tokens},
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def query(self, question: str, top_k: int) -> list[BM25Hit]:
        if not self.documents or top_k <= 0:
            return []
        query_tokens = tokenize(question)
        scores = self._ranker.get_scores(query_tokens)
        scored: list[tuple[int, float]] = []
        for index, score in enumerate(scores):
            overlap = len(set(query_tokens).intersection(self.tokens[index]))
            if overlap:
                # rank_bm25 can return zero for a unique term in a two-document corpus;
                # the tiny lexical tie-breaker keeps that deterministic and meaningful.
                scored.append((index, float(score) + overlap * 1e-6))
        ranked = sorted(scored, key=lambda item: (-item[1], self.documents[item[0]].table_name))
        return [BM25Hit(str(index), score) for index, score in ranked[:top_k]]
