from __future__ import annotations

from collections.abc import Sequence

from ingest.models import DocumentChunk
from retrieval.embeddings import LocalHashEmbedder
from retrieval.lexical import _to_hit
from retrieval.models import SearchHit


class LocalDenseIndex:
    """Deterministic local dense baseline using hashed token vectors."""

    def __init__(self, chunks: Sequence[DocumentChunk], dimensions: int = 768):
        self.chunks = list(chunks)
        self.embedder = LocalHashEmbedder(dimensions)
        self.vectors = [self._encode(f"{c.title} {c.reference} {c.text}") for c in self.chunks]

    def _encode(self, text: str) -> list[float]:
        return self.embedder.encode([text])[0]

    def search(self, query: str, limit: int = 20) -> list[SearchHit]:
        query_vector = self._encode(query)
        ranked = [
            (sum(a * b for a, b in zip(query_vector, vector, strict=True)), chunk)
            for vector, chunk in zip(self.vectors, self.chunks, strict=True)
            if chunk.is_primary
        ]
        ranked = [item for item in ranked if item[0] > 0]
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [_to_hit(chunk, score, "dense_score") for score, chunk in ranked[:limit]]
