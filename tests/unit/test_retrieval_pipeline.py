from ingest.models import DocumentChunk
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.lexical import BM25Index
from retrieval.models import SearchHit
from retrieval.rerank import IdentityReranker
from retrieval.tokenization import tokenize


def chunk(chunk_id: str, reference: str, doc_type: str, text: str) -> DocumentChunk:
    collection = {"fiche_technique": "fiches_techniques", "notice": "notices"}[doc_type]
    return DocumentChunk(
        chunk_id=chunk_id, doc_id=chunk_id, family_id=chunk_id, text=text,
        title=f"{doc_type} {reference}", reference=reference, version="1.0",
        date="2025-01-01", doc_type=doc_type, collection=collection,
        source_path=f"{chunk_id}.pdf", content_hash=chunk_id, chunk_index=0,
    )


def hit(chunk_id: str, score: float) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id, doc_id=chunk_id, score=score, text="text", title="title",
        reference="REF-1", version="1", date="2025-01-01", doc_type="fiche_technique",
        collection="fiches_techniques", source_path=f"{chunk_id}.pdf",
    )


def test_tokenizer_preserves_exact_reference():
    assert "ref-8842" in tokenize("Fiche REF 8842")


def test_bm25_prioritizes_technical_sheet_for_bare_reference():
    index = BM25Index([
        chunk("notice", "REF-8842", "notice", "Installation REF-8842"),
        chunk("sheet", "REF-8842", "fiche_technique", "Technical data REF-8842"),
    ])
    hits = index.search("REF-8842")
    assert hits[0].doc_type == "fiche_technique"


def test_rrf_rewards_hit_present_in_both_rankings():
    fused = reciprocal_rank_fusion([[hit("a", 10), hit("b", 9)], [hit("b", 3), hit("c", 2)]])
    assert fused[0].chunk_id == "b"
    assert fused[0].rrf_score is not None


def test_identity_reranker_limits_without_reordering():
    reranked = IdentityReranker().rerank("query", [hit("a", 2), hit("b", 1)], limit=1)
    assert [item.chunk_id for item in reranked] == ["a"]
