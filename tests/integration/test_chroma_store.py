import chromadb

from ingest.chroma_store import ChromaVectorStore
from ingest.models import DocumentChunk
from retrieval.embeddings import LocalHashEmbedder


def test_chroma_upsert_is_idempotent_and_search_preserves_metadata():
    chunk = DocumentChunk(
        chunk_id="chunk-1", doc_id="doc-1", family_id="family-1", text="motor circuit breaker",
        title="Motor protection", reference="REF-8842", version="2.1", date="2025-01-01",
        doc_type="fiche_technique", collection="fiches_techniques", source_path="sheet.pdf",
        content_hash="hash", chunk_index=0,
    )
    store = ChromaVectorStore(chromadb.EphemeralClient(), LocalHashEmbedder(64), "test_collection")

    store.upsert([chunk])
    store.upsert([chunk])
    hits = store.search("motor breaker", limit=1)

    assert store.count() == 1
    assert hits[0].reference == "REF-8842"
    assert hits[0].doc_type == "fiche_technique"
