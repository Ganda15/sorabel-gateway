from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ingest.models import DocumentChunk
from retrieval.embeddings import Embedder
from retrieval.models import SearchHit


class ChromaVectorStore:
    def __init__(self, client: Any, embedder: Embedder, collection_name: str = "sorabel_documents"):
        self.embedder = embedder
        self.collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    @staticmethod
    def _metadata(chunk: DocumentChunk) -> dict[str, str | int | bool]:
        return {
            "doc_id": chunk.doc_id, "family_id": chunk.family_id, "title": chunk.title,
            "reference": chunk.reference, "version": chunk.version, "date": chunk.date,
            "doc_type": chunk.doc_type, "collection": chunk.collection,
            "source_path": chunk.source_path, "chunk_index": chunk.chunk_index,
            "is_primary": chunk.is_primary,
        }

    def upsert(self, chunks: Sequence[DocumentChunk]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[self._metadata(chunk) for chunk in chunks],
            embeddings=self.embedder.encode([f"passage: {chunk.text}" for chunk in chunks]),
        )

    def count(self) -> int:
        return int(self.collection.count())

    def search(self, query: str, limit: int = 5, where: dict | None = None) -> list[SearchHit]:
        result = self.collection.query(
            query_embeddings=self.embedder.encode([f"query: {query}"]),
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[SearchHit] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances, strict=True):
            if metadata is None or text is None:
                continue
            score = 1.0 - float(distance)
            hits.append(
                SearchHit.model_validate(
                    {
                        "chunk_id": chunk_id,
                        "doc_id": str(metadata["doc_id"]),
                        "score": score,
                        "dense_score": score,
                        "text": text,
                        "title": str(metadata["title"]),
                        "reference": str(metadata.get("reference", "")),
                        "version": str(metadata["version"]),
                        "date": str(metadata["date"]),
                        "doc_type": str(metadata["doc_type"]),
                        "collection": str(metadata["collection"]),
                        "source_path": str(metadata["source_path"]),
                        "is_primary": bool(metadata.get("is_primary", True)),
                    }
                )
            )
        return hits
