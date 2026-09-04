from retrieval.models import AnswerResult, CitationSource, SearchHit


def test_search_hit_serializes_the_acceptance_contract():
    hit = SearchHit(
        chunk_id="fiche-ref-8842-v2.1::0003",
        doc_id="fiche-ref-8842-v2.1",
        score=0.92,
        text="Disjoncteur adapté à un départ moteur triphasé.",
        title="Fiche technique REF-8842",
        reference="ref 8842",
        version="2.1",
        date="2025-09-18",
        doc_type="fiche_technique",
        collection="fiches_techniques",
        source_path="data/corpus/fiches/REF-8842-v2.1.pdf",
    )

    payload = hit.to_payload()

    assert payload["doc_id"] == "fiche-ref-8842-v2.1"
    assert payload["score"] == 0.92
    assert payload["text"] == hit.text
    assert payload["metadata"]["reference"] == "REF-8842"
    assert payload["metadata"]["doc_type"] == "fiche_technique"
    assert payload["metadata"]["version"] == "2.1"
    assert payload["metadata"]["date"] == "2025-09-18"

def test_answer_result_serializes_a_cited_answer():
    source = CitationSource(
        titre="Fiche technique REF-8842",
        reference="ref 8842",
        date="2025-09-18",
    )
    result = AnswerResult(
        status="ok",
        answer="Ce disjoncteur convient à un départ moteur triphasé.",
        sources=[source],
    )

    envelope = result.to_envelope()

    assert envelope["status"] == "ok"
    assert envelope["payload"]["answer"] == result.answer
    assert envelope["payload"]["sources"] == [
        {
            "titre": "Fiche technique REF-8842",
            "reference": "REF-8842",
            "date": "2025-09-18",
        }
    ]


def test_answer_result_serializes_outside_corpus_without_an_answer():
    result = AnswerResult(
        status="hors_corpus",
        message="Le corpus ne contient pas de preuve suffisante.",
    )

    envelope = result.to_envelope()

    assert envelope["status"] == "hors_corpus"
    assert envelope["payload"] == {}
    assert envelope["message"]    