from __future__ import annotations

from collections.abc import Sequence

from retrieval.models import SearchHit


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[SearchHit]],
    k: int = 60,
) -> list[SearchHit]:
    scores: dict[str, float] = {}
    hits: dict[str, SearchHit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            if hit.chunk_id not in hits:
                hits[hit.chunk_id] = hit
            else:
                current = hits[hit.chunk_id]
                updates = {
                    "dense_score": hit.dense_score if hit.dense_score is not None else current.dense_score,
                    "lexical_score": hit.lexical_score if hit.lexical_score is not None else current.lexical_score,
                }
                hits[hit.chunk_id] = current.model_copy(update=updates)
    fused = [hit.model_copy(update={"score": scores[key], "rrf_score": scores[key]}) for key, hit in hits.items()]
    return sorted(fused, key=lambda item: (-item.score, item.chunk_id))
