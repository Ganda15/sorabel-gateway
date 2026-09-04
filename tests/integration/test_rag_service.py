from pathlib import Path

from retrieval.service import build_local_service


def test_real_corpus_exact_reference_and_profile_filter():
    service = build_local_service(Path("data/corpus"), Path("data/index"))

    hits = service.search_docs("REF-8842", profile="support", limit=3)
    sources = service.list_sources("support")

    assert hits[0].reference == "REF-8842"
    assert hits[0].doc_type == "fiche_technique"
    assert all(source.doc_type != "note_interne" for source in sources)


def test_answer_is_cited_or_refused_without_invention():
    service = build_local_service(Path("data/corpus"), Path("data/index"))

    covered = service.answer_question(
        "quelle est la procédure de retour d'un produit défectueux sous garantie ?",
        profile="support",
    )
    outside = service.answer_question("quelle est la politique de télétravail chez Sorabel ?", profile="support")

    assert covered.status == "ok"
    assert covered.answer
    assert covered.sources and covered.sources[0].titre
    assert outside.status == "hors_corpus"
    assert not outside.answer


def test_answer_prefers_the_passage_that_contains_the_requested_fact():
    service = build_local_service(Path("data/corpus"), Path("data/index"))

    result = service.answer_question(
        "Quelle est la tension assignée du produit REF-8842 ?",
        profile="support",
    )

    assert result.status == "ok"
    assert "230/400 V AC" in result.answer
    assert any(source.reference == "REF-8842" for source in result.sources)
