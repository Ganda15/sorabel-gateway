from ingest.catalog import build_catalog, normalized_content_hash, version_key
from ingest.models import CanonicalDocument


def document(doc_id: str, version: str, text: str, doc_type: str = "fiche_technique"):
    collection = "fiches_techniques" if doc_type == "fiche_technique" else "notices"
    return CanonicalDocument(
        doc_id=doc_id, family_id="family", title="Product", reference="REF-8842",
        version=version, date="2025-01-01", doc_type=doc_type, collection=collection,
        source_path=f"{doc_id}.pdf", content_hash=normalized_content_hash(text), text=text,
    )


def test_catalog_selects_latest_version_and_keeps_history():
    catalog = build_catalog([document("old", "1.9", "old"), document("new", "2.1", "new")])

    assert [item.doc_id for item in catalog.documents] == ["old", "new"]
    assert catalog.get("new").is_primary is True
    assert catalog.get("old").is_primary is False
    assert catalog.stats.versions == 2


def test_catalog_deduplicates_equal_normalized_content():
    catalog = build_catalog([document("one", "1.0", "Same   text"), document("two", "1.0", "same text")])
    assert len(catalog.documents) == 1
    assert catalog.stats.duplicates == 1


def test_version_key_is_numeric():
    assert version_key("2.10") > version_key("2.9")
