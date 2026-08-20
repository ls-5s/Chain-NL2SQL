"""Combine vector and BM25 candidates before reranking."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.bm25_store import BM25Hit
from app.rag.reranker import Reranker
from app.rag.vector_store import VectorHit
from app.schemas.domain import SchemaDocument


@dataclass(frozen=True)
class RankedSchema:
    document: SchemaDocument
    score: float


def reciprocal_rank_fusion(
    documents: list[SchemaDocument],
    bm25_hits: list[BM25Hit],
    vector_hits: list[VectorHit],
    *,
    top_k: int,
    reranker: Reranker | None = None,
    question: str = "",
) -> list[RankedSchema]:
    by_id = {str(index): document for index, document in enumerate(documents)}
    scores: dict[str, float] = {}
    for rank, hit in enumerate(bm25_hits, start=1):
        if hit.document_id in by_id:
            scores[hit.document_id] = scores.get(hit.document_id, 0.0) + 1.0 / (60 + rank)
    for rank, hit in enumerate(vector_hits, start=1):
        if hit.document_id in by_id:
            scores[hit.document_id] = scores.get(hit.document_id, 0.0) + 1.0 / (60 + rank)

    ranked_ids = sorted(scores, key=lambda item: (-scores[item], by_id[item].table_name))
    if reranker and ranked_ids:
        candidates = [by_id[item] for item in ranked_ids]
        rerank_scores = reranker.rerank(question, [item.content for item in candidates])
        reranked = sorted(
            zip(rerank_scores, ranked_ids), key=lambda pair: (-float(pair[0]), by_id[pair[1]].table_name)
        )
        ranked_ids = [item for _, item in reranked]
        scores = {item: float(score) for score, item in reranked}
    return [RankedSchema(by_id[item], scores[item]) for item in ranked_ids[:top_k]]
