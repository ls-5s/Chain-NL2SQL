"""ChromaDB storage with an injectable embedding provider."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from app.rag.retriever import SchemaRetrievalError
from app.schemas.domain import SchemaDocument


class EmbeddingProvider(Protocol):
    model_name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedding:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:  # pragma: no cover - environment dependent
            raise SchemaRetrievalError("Embedding dependency is unavailable.") from error
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], normalize_embeddings=True)[0].tolist()


@dataclass(frozen=True)
class VectorHit:
    document_id: str
    score: float


class ChromaVectorStore:
    def __init__(self, path: str | Path, collection_name: str, embedding: EmbeddingProvider) -> None:
        try:
            import chromadb
        except ImportError as error:  # pragma: no cover - environment dependent
            raise SchemaRetrievalError("ChromaDB dependency is unavailable.") from error
        self._client = chromadb.PersistentClient(path=str(path))
        self._collection = self._client.get_or_create_collection(name=collection_name)
        self.embedding = embedding

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            close()

    def build(self, documents: Iterable[SchemaDocument]) -> None:
        items = list(documents)
        if not items:
            return
        ids = [str(index) for index in range(len(items))]
        self._collection.upsert(
            ids=ids,
            documents=[doc.content for doc in items],
            metadatas=[
                {"database_id": doc.database_id, "table_name": doc.table_name, "dialect": doc.dialect}
                for doc in items
            ],
            embeddings=self.embedding.embed_documents([doc.content for doc in items]),
        )

    def query(self, question: str, database_id: str, top_k: int) -> list[VectorHit]:
        result = self._collection.query(
            query_embeddings=[self.embedding.embed_query(question)],
            n_results=max(1, top_k),
            where={"database_id": database_id},
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [VectorHit(str(doc_id), 1.0 - float(distance)) for doc_id, distance in zip(ids, distances)]
