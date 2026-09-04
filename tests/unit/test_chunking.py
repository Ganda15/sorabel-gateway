from ingest.chunking import chunk_document
from ingest.models import CanonicalDocument


def sample(text: str) -> CanonicalDocument:
    return CanonicalDocument(
        doc_id="doc", family_id="family", title="Title", reference="REF-8842",
        version="2.1", date="2025-09-18", doc_type="fiche_technique",
        collection="fiches_techniques", source_path="fiches/ref.pdf",
        content_hash="abc", text=text,
    )


def test_chunks_preserve_citation_metadata_and_are_stable():
    text = "First short paragraph.\n\n" + "Second sentence. " * 30
    first = chunk_document(sample(text), target_chars=120, overlap_chars=25)
    second = chunk_document(sample(text), target_chars=120, overlap_chars=25)

    assert len(first) > 1
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert [chunk.chunk_index for chunk in first] == list(range(len(first)))
    assert all(chunk.reference == "REF-8842" for chunk in first)
    assert all(chunk.date == "2025-09-18" for chunk in first)


def test_short_table_remains_one_chunk():
    chunks = chunk_document(sample("Name | Value\n--- | ---\nPower | 10 kW"), target_chars=100)
    assert len(chunks) == 1
    assert "Power | 10 kW" in chunks[0].text
