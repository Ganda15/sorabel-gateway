from __future__ import annotations

import re
from pathlib import Path

from application import policy
from ingest.models import CanonicalDocument, DocumentChunk
from ingest.pipeline import ingest_corpus, load_index
from retrieval.dense import LocalDenseIndex
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.lexical import BM25Index
from retrieval.models import AnswerResult, CitationSource, SearchHit
from retrieval.rerank import IdentityReranker
from retrieval.tokenization import tokenize


#: Axe *collection* de la matrice d'acces, lu dans application/access_policy.json.
#: Le filtre est applique AVANT le classement : un document interdit n'entre
#: jamais dans les candidats, meme avec un score eleve.
COLLECTIONS_BY_PROFILE = policy.collections_by_profile()


class RagService:
    def __init__(self, documents: list[CanonicalDocument], chunks: list[DocumentChunk]):
        self.documents = documents
        self.chunks = chunks
        self.dense = LocalDenseIndex(chunks)
        self.lexical = BM25Index(chunks)
        self.reranker = IdentityReranker()

    @staticmethod
    def _allowed(profile: str) -> set[str]:
        try:
            return COLLECTIONS_BY_PROFILE[profile]
        except KeyError as exc:
            raise ValueError(f"Unknown profile: {profile}") from exc

    def search_docs(self, query: str, profile: str, limit: int = 5, mode: str = "hybrid") -> list[SearchHit]:
        if not query.strip():
            raise ValueError("Query must not be empty")
        allowed = self._allowed(profile)
        dense = [hit for hit in self.dense.search(query, 30) if hit.collection in allowed]
        if mode == "dense":
            return dense[:limit]
        lexical = [hit for hit in self.lexical.search(query, 30) if hit.collection in allowed]
        if mode != "hybrid":
            raise ValueError(f"Unknown retrieval mode: {mode}")
        fused = reciprocal_rank_fusion([dense, lexical])
        tokens = tokenize(query)
        if len(tokens) == 1 and tokens[0].startswith("ref-"):
            fused.sort(
                key=lambda hit: (
                    hit.reference.casefold() != tokens[0],
                    hit.doc_type != "fiche_technique",
                    -hit.score,
                    hit.chunk_id,
                )
            )
        return self.reranker.rerank(query, fused, limit)

    def get_document(self, doc_id: str, profile: str, version: str | None = None) -> CanonicalDocument:
        allowed = self._allowed(profile)
        candidates = [d for d in self.documents if d.doc_id == doc_id or d.family_id == doc_id]
        if version is not None:
            candidates = [d for d in candidates if d.version == version]
        candidates = [d for d in candidates if d.collection in allowed]
        if not candidates:
            raise KeyError(doc_id)
        return max(candidates, key=lambda item: (item.is_primary, item.version))

    def list_sources(self, profile: str) -> list[CanonicalDocument]:
        allowed = self._allowed(profile)
        return [d for d in self.documents if d.is_primary and d.collection in allowed]

    def answer_question(self, question: str, profile: str) -> AnswerResult:
        hits = self.search_docs(question, profile, limit=5)
        query_terms = set(tokenize(question))
        evidence = [hit for hit in hits if len(query_terms.intersection(tokenize(hit.text + " " + hit.title))) >= 2]
        if not evidence:
            return AnswerResult(
                status="hors_corpus",
                message="Insufficient documentary evidence in the authorized corpus.",
            )

        reference_terms = {term for term in query_terms if term.startswith("ref-")}
        if reference_terms:
            exact_reference = [hit for hit in evidence if hit.reference.casefold() in reference_terms]
            if exact_reference:
                evidence = exact_reference

        focus_terms = query_terms - reference_terms - {"produit", "reference"}
        focus_terms = focus_terms or query_terms
        candidates: list[tuple[int, int, float, SearchHit, str]] = []
        for hit in evidence:
            parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", hit.text) if part.strip()]
            for part in parts:
                part_terms = set(tokenize(part))
                candidates.append(
                    (
                        len(focus_terms.intersection(part_terms)),
                        len(query_terms.intersection(part_terms)),
                        hit.score,
                        hit,
                        part,
                    )
                )

        best_focus = max(candidate[0] for candidate in candidates)
        if best_focus:
            candidates = [candidate for candidate in candidates if candidate[0] == best_focus]
        candidates.sort(key=lambda candidate: (-candidate[0], -candidate[1], -candidate[2], candidate[4]))

        selected: list[tuple[SearchHit, str]] = []
        seen_sentences: set[str] = set()
        for _, _, _, hit, sentence in candidates:
            if sentence not in seen_sentences:
                selected.append((hit, sentence))
                seen_sentences.add(sentence)
            if len(selected) == 2:
                break

        sentences = [sentence for _, sentence in selected]
        sources = [
            CitationSource(titre=hit.title, reference=hit.reference or "GENERAL", date=hit.date)
            for hit, _ in selected
        ]
        return AnswerResult(status="ok", answer=" ".join(dict.fromkeys(sentences)), sources=sources)


def build_local_service(corpus_root: Path, index_root: Path) -> RagService:
    if not (index_root / "manifest.json").exists():
        ingest_corpus(corpus_root, index_root)
    documents, chunks = load_index(index_root)
    return RagService(documents, chunks)
