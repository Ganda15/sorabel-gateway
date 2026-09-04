from __future__ import annotations

from collections.abc import Sequence

from rank_bm25 import BM25Okapi

from ingest.models import DocumentChunk
from retrieval.models import SearchHit
from retrieval.tokenization import tokenize


def _to_hit(chunk: DocumentChunk, score: float, field: str) -> SearchHit:
    hit = SearchHit(
        chunk_id=chunk.chunk_id, doc_id=chunk.doc_id, score=score, text=chunk.text,
        title=chunk.title, reference=chunk.reference, version=chunk.version, date=chunk.date,
        doc_type=chunk.doc_type, collection=chunk.collection, source_path=chunk.source_path,
        is_primary=chunk.is_primary,
    )
    return hit.model_copy(update={field: score})


class BM25Index:
    def __init__(self, chunks: Sequence[DocumentChunk]):
        self.chunks = list(chunks)
        corpus = [
            tokenize(f"{chunk.title} {chunk.title} {chunk.reference} {chunk.reference} {chunk.doc_type} {chunk.text}")
            for chunk in self.chunks
        ]
        self.index = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, limit: int = 20) -> list[SearchHit]:
        if self.index is None:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        scores = self.index.get_scores(query_tokens)
        bare_reference = len(query_tokens) == 1 and query_tokens[0].startswith("ref-")
        ranked: list[tuple[float, DocumentChunk]] = []
        for score, chunk in zip(scores, self.chunks, strict=True):
            adjusted = float(score)
            if query_tokens[0].startswith("ref-") and chunk.reference.casefold() == query_tokens[0]:
                adjusted += 20.0
                if bare_reference and chunk.doc_type == "fiche_technique":
                    adjusted += 5.0
            if adjusted > 0 and chunk.is_primary:
                ranked.append((adjusted, chunk))
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [_to_hit(chunk, score, "lexical_score") for score, chunk in ranked[:limit]]
