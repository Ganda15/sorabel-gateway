from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from retrieval.models import SearchHit


class IdentityReranker:
    def rerank(self, query: str, hits: Sequence[SearchHit], limit: int) -> list[SearchHit]:
        del query
        return list(hits[:limit])


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model: Any = None

    def rerank(self, query: str, hits: Sequence[SearchHit], limit: int) -> list[SearchHit]:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        scores = self._model.predict([(query, hit.text) for hit in hits])
        reranked = [hit.model_copy(update={"score": float(score), "rerank_score": float(score)}) for hit, score in zip(hits, scores, strict=True)]
        return sorted(reranked, key=lambda item: (-item.score, item.chunk_id))[:limit]
