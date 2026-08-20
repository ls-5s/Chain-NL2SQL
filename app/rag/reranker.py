"""Injectable cross-encoder reranking for schema candidates."""

from __future__ import annotations

from typing import Protocol

from app.rag.retriever import SchemaRetrievalError


class Reranker(Protocol):
    model_name: str

    def rerank(self, question: str, documents: list[str]) -> list[float]: ...


class SentenceTransformerReranker:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as error:  # pragma: no cover - environment dependent
            raise SchemaRetrievalError("Reranker dependency is unavailable.") from error
        self._model = CrossEncoder(model_name)

    def rerank(self, question: str, documents: list[str]) -> list[float]:
        return [float(value) for value in self._model.predict([(question, document) for document in documents])]
