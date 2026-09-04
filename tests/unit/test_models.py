from ingest.models import CanonicalDocument, DocumentChunk, normalize_reference


def test_normalize_reference_uses_canonical_format():
    assert normalize_reference("ref-8842") == "REF-8842"
    assert normalize_reference(" Ref 8842 ") == "REF-8842"
    assert normalize_reference("REF-8842") == "REF-8842"


def test_canonical_document_keeps_required_metadata():
    document = CanonicalDocument(
        doc_id="fiche-ref-8842-v2.1",
        family_id="fiche-ref-8842",
        title="Fiche technique REF-8842",
        reference="ref 8842",
        version="2.1",
        date="2025-09-18",
        doc_type="fiche_technique",
        collection="fiches_techniques",
        source_path="data/corpus/fiches/REF-8842-v2.1.pdf",
        content_hash="sha256:test",
        text="Disjoncteur adapté à un départ moteur triphasé.",
    )

    assert document.reference == "REF-8842"
    assert document.title == "Fiche technique REF-8842"
    assert document.version == "2.1"
    assert document.date == "2025-09-18"

def test_document_chunk_keeps_search_and_citation_metadata():
    chunk = DocumentChunk(
        chunk_id="fiche-ref-8842-v2.1::0003",
        doc_id="fiche-ref-8842-v2.1",
        family_id="fiche-ref-8842",
        text="Disjoncteur adapté à un départ moteur triphasé.",
        title="Fiche technique REF-8842",
        reference="ref 8842",
        version="2.1",
        date="2025-09-18",
        doc_type="fiche_technique",
        collection="fiches_techniques",
        source_path="data/corpus/fiches/REF-8842-v2.1.pdf",
        content_hash="sha256:test",
        chunk_index=3,
    )

    assert chunk.chunk_id == "fiche-ref-8842-v2.1::0003"
    assert chunk.reference == "REF-8842"
    assert chunk.chunk_index == 3
    assert chunk.is_primary is True    