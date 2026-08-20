"""Manage schema index versions and controlled rebuilds."""

from __future__ import annotations

import json
import gc
import os
import re
import tempfile
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock

from app.rag.bm25_store import BM25Store
from app.rag.bm25_store import TOKENIZER_VERSION
from app.rag.hybrid_retriever import reciprocal_rank_fusion
from app.rag.reranker import Reranker, SentenceTransformerReranker
from app.rag.retriever import SchemaRetrievalError, SchemaRetrievalRequest
from app.rag.vector_store import ChromaVectorStore, EmbeddingProvider, SentenceTransformerEmbedding
from app.schemas.domain import SchemaDocument, SchemaRetrieval


class SchemaIndexManager:
    """Lazy, versioned Schema index with permission-aware retrieval."""

    _locks: dict[str, threading.RLock] = {}
    _locks_guard = threading.Lock()

    def __init__(
        self,
        schema_source: Callable[[str], SchemaRetrieval],
        *,
        root: str | Path = "data/schema_metadata",
        mode: str = "hybrid",
        top_k: int = 5,
        fallback_mode: str = "bm25",
        embedding_factory: Callable[[], EmbeddingProvider] | None = None,
        reranker_factory: Callable[[], Reranker] | None = None,
        embedding_model_name: str | None = None,
        reranker_model_name: str | None = None,
    ) -> None:
        if mode not in {"vector", "bm25", "hybrid"}:
            raise ValueError("mode must be vector, bm25, or hybrid")
        if fallback_mode not in {"none", "bm25"}:
            raise ValueError("fallback_mode must be none or bm25")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        self.schema_source = schema_source
        self.root = Path(root)
        self.mode = mode
        self.top_k = top_k
        self.fallback_mode = fallback_mode
        self.embedding_factory = embedding_factory
        self.reranker_factory = reranker_factory
        self.embedding_model_name = embedding_model_name
        self.reranker_model_name = reranker_model_name

    def retrieve(self, request: SchemaRetrievalRequest) -> SchemaRetrieval:
        try:
            full = self.schema_source(request.database_id)
            documents = self._authorized_documents(full.documents, request)
        except SchemaRetrievalError:
            raise
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise SchemaRetrievalError("Unable to read the Schema index source.") from error
        if not documents:
            return SchemaRetrieval(documents=[], schema_version=full.schema_version, retrieval_mode=self.mode)
        scope_hash = _scope_hash(request, documents)
        index_path = self.root / _safe_component(request.database_id) / full.schema_version / scope_hash
        lock_path = index_path.parent / f".{scope_hash}.lock"
        with self._lock_for(str(index_path)):
            try:
                with FileLock(str(lock_path), timeout=60):
                    manifest = self._ensure_index(index_path, documents, full.schema_version, request.dialect, scope_hash)
            except SchemaRetrievalError:
                raise
            except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
                raise SchemaRetrievalError("Schema index is unavailable.") from error
            try:
                bm25 = BM25Store.load(index_path) if manifest["bm25_available"] else None
            except Exception as error:
                if self.fallback_mode == "none":
                    raise SchemaRetrievalError("BM25 Schema index is unavailable.") from error
                bm25 = None
            vector = None
            vector_error: Exception | None = None
            if self.mode in {"vector", "hybrid"} and manifest.get("vector_available"):
                try:
                    vector = ChromaVectorStore(
                        index_path / "vector",
                        _collection_name(request.database_id, full.schema_version, scope_hash),
                        self._embedding(),
                    )
                except Exception as error:  # dependency/model/storage failures are handled below
                    vector_error = error
            if self.mode == "vector" and vector is None:
                if self.fallback_mode != "bm25" or bm25 is None:
                    raise SchemaRetrievalError("Vector Schema retrieval is unavailable.") from vector_error
                mode = "bm25"
            else:
                mode = self.mode
            bm25_hits = bm25.query(request.question, max(self.top_k * 2, 10)) if bm25 and mode in {"bm25", "hybrid"} else []
            try:
                vector_hits = (
                    vector.query(request.question, request.database_id, max(self.top_k * 2, 10))
                    if vector and mode in {"vector", "hybrid"}
                    else []
                )
            except Exception as error:
                if self.fallback_mode == "none":
                    raise SchemaRetrievalError("Vector Schema retrieval is unavailable.") from error
                vector_hits = []
                mode = "bm25" if bm25 is not None else mode
            if mode == "bm25" and bm25 is not None:
                bm25_hits = bm25.query(request.question, max(self.top_k * 2, 10))
                vector_hits = []
            ranked_documents_source = documents
            reranker = None
            if mode in {"vector", "hybrid"}:
                try:
                    reranker = self._reranker()
                except Exception as error:
                    if self.fallback_mode == "none":
                        raise SchemaRetrievalError("Schema reranker is unavailable.") from error
                    mode = "bm25"
            ranked = reciprocal_rank_fusion(
                ranked_documents_source,
                bm25_hits,
                vector_hits,
                top_k=self.top_k,
                reranker=reranker,
                question=request.question,
            )
            if not ranked and mode != "bm25" and bm25 is not None:
                mode = "bm25"
                ranked = reciprocal_rank_fusion(
                    ranked_documents_source,
                    bm25.query(request.question, max(self.top_k * 2, 10)),
                    [],
                    top_k=self.top_k,
                )
            ranked_documents = [item.document for item in ranked]
            if vector is not None:
                vector.close()
            return SchemaRetrieval(
                documents=ranked_documents,
                schema_version=full.schema_version,
                retrieval_mode=mode,
                retrieval_scores={document.table_name: item.score for document, item in zip(ranked_documents, ranked)},
            )

    def _ensure_index(
        self,
        path: Path,
        documents: list[SchemaDocument],
        version: str,
        dialect: str,
        scope_hash: str,
    ) -> dict[str, object]:
        manifest_path = path / "manifest.json"
        if manifest_path.exists() and (path / "bm25.json").exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                vector_ready = bool(manifest.get("vector_available"))
                vector_requirement_satisfied = self.mode == "bm25" or vector_ready or self.fallback_mode == "bm25"
                models_match = (
                    self.embedding_model_name is None
                    or manifest.get("embedding_model") in {None, self.embedding_model_name}
                ) and (
                    self.reranker_model_name is None
                    or manifest.get("reranker_model") in {None, self.reranker_model_name}
                )
                if (
                    manifest.get("schema_version") == version
                    and manifest.get("document_count") == len(documents)
                    and manifest.get("scope_hash") == scope_hash
                    and manifest.get("tokenizer_version") == TOKENIZER_VERSION
                    and vector_requirement_satisfied
                    and models_match
                ):
                    return manifest
            except (OSError, ValueError, KeyError):
                pass
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=path.parent))
        try:
            BM25Store.build(temp_path, documents)
            manifest: dict[str, object] = {
                "database_id": documents[0].database_id if documents else "",
                "schema_version": version,
                "scope_hash": scope_hash,
                "tokenizer_version": TOKENIZER_VERSION,
                "dialect": dialect,
                "document_count": len(documents),
                "document_fingerprints": [_fingerprint(document) for document in documents],
                "embedding_model": self.embedding_model_name,
                "reranker_model": self.reranker_model_name,
                "built_at": datetime.now(timezone.utc).isoformat(),
                "bm25_available": True,
                "vector_available": False,
            }
            if self.mode in {"vector", "hybrid"}:
                vector = None
                try:
                    embedding = self._embedding()
                    vector = ChromaVectorStore(
                        temp_path / "vector",
                        _collection_name(documents[0].database_id if documents else "schema", version, scope_hash),
                        embedding,
                    )
                    vector.build(documents)
                    manifest["vector_available"] = True
                    manifest["embedding_model"] = embedding.model_name
                except Exception as error:
                    if self.fallback_mode == "none":
                        raise SchemaRetrievalError("Vector Schema index could not be built.") from error
                finally:
                    if vector is not None:
                        vector.close()
            # Chroma's SQLite client can hold Windows file handles until collected.
            gc.collect()
            (temp_path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            backup_path = path.parent / f".{path.name}.backup-{os.getpid()}-{threading.get_ident()}"
            if backup_path.exists():
                _remove_tree(backup_path)
            moved_old = False
            try:
                if path.exists():
                    os.replace(path, backup_path)
                    moved_old = True
                os.replace(temp_path, path)
            except Exception:
                if moved_old and not path.exists() and backup_path.exists():
                    os.replace(backup_path, path)
                raise
            finally:
                if backup_path.exists():
                    _remove_tree(backup_path)
            return manifest
        except Exception:
            _remove_tree(temp_path)
            raise

    def _embedding(self) -> EmbeddingProvider:
        if self.embedding_factory is None:
            raise SchemaRetrievalError("Embedding provider is not configured.")
        return self.embedding_factory()

    def _reranker(self) -> Reranker:
        if self.reranker_factory is None:
            raise SchemaRetrievalError("Reranker is not configured.")
        return self.reranker_factory()

    @classmethod
    def _lock_for(cls, lock_key: str) -> threading.RLock:
        with cls._locks_guard:
            return cls._locks.setdefault(lock_key, threading.RLock())

    @staticmethod
    def _authorized_documents(documents: list[SchemaDocument], request: SchemaRetrievalRequest) -> list[SchemaDocument]:
        allowed_tables = {item.lower() for item in request.allowed_tables}
        allowed_columns = {table.lower(): {column.lower() for column in columns} for table, columns in request.allowed_columns.items()}
        result: list[SchemaDocument] = []
        for document in documents:
            if document.database_id != request.database_id:
                continue
            if allowed_tables and document.table_name.lower() not in allowed_tables:
                continue
            table_columns = allowed_columns.get(document.table_name.lower())
            if document.table_name.lower() in allowed_columns:
                visible_columns = [column for column in document.column_names if column.lower() in table_columns]
                content = document.content if len(visible_columns) == len(document.column_names) else _filter_content_columns(document, visible_columns)
                result.append(document.model_copy(update={"column_names": visible_columns, "content": content}))
            else:
                result.append(document)
        return result


def _filter_content_columns(document: SchemaDocument, visible_columns: list[str]) -> str:
    lines = document.content.splitlines()
    columns = ", ".join(line for line in lines if line.startswith("COLUMNS ")).removeprefix("COLUMNS ")
    visible = [part.strip() for part in columns.split(",") if part.strip().split(" ", 1)[0] in visible_columns]
    primary_key = [
        column.strip()
        for column in next((line.removeprefix("PRIMARY KEY ") for line in lines if line.startswith("PRIMARY KEY ")), "").split(",")
        if column.strip() in visible_columns
    ]
    return "\n".join(
        [
            f"TABLE {document.table_name}",
            f"COLUMNS {', '.join(visible)}",
            f"PRIMARY KEY {', '.join(primary_key) if primary_key else 'none'}",
            "FOREIGN KEYS none",
        ]
    )


def _fingerprint(document: SchemaDocument) -> str:
    import hashlib
    return hashlib.sha256(document.content.encode("utf-8")).hexdigest()


def _safe_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def _scope_hash(request: SchemaRetrievalRequest, documents: list[SchemaDocument]) -> str:
    import hashlib

    scope = {
        "database_id": request.database_id,
        "allowed_tables": sorted(document.table_name.lower() for document in documents),
        "allowed_columns": {
            table.lower(): sorted(column.lower() for column in columns)
            for table, columns in request.allowed_columns.items()
        },
    }
    return hashlib.sha256(json.dumps(scope, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def _collection_name(database_id: str, version: str, scope_hash: str) -> str:
    return _safe_component(f"schema_{database_id}_{version[:12]}_{scope_hash[:12]}")[:63]


def _remove_tree(path: Path) -> None:
    import shutil
    shutil.rmtree(path, ignore_errors=True)
