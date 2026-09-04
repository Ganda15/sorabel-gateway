from pathlib import Path

import pytest

from ingest.parsers import parse_document


def test_parse_markdown_front_matter(tmp_path: Path):
    path = tmp_path / "notes" / "note-2026-01-01.md"
    path.parent.mkdir()
    path.write_text(
        "---\ntitre: Quality note\ndate: 2026-01-01\n"
        "type: note_interne\nversion: '2.0'\n---\n\n# Quality note\n\nREF-8842 is checked.",
        encoding="utf-8",
    )

    document = parse_document(path, tmp_path)

    assert document.title == "Quality note"
    assert document.date == "2026-01-01"
    assert document.version == "2.0"
    assert document.reference == "REF-8842"
    assert document.collection == "notes_internes"
    assert "titre:" not in document.text


def test_parse_html_metadata_and_visible_text(tmp_path: Path):
    path = tmp_path / "sav" / "proc-retour-REF-1000-v2.0.html"
    path.parent.mkdir()
    path.write_text(
        "<html><head><title>Return procedure</title>"
        '<meta name="version" content="2.0"><meta name="date" content="2025-09-18">'
        '<meta name="type" content="procedure_sav"></head>'
        "<body><h1>Return procedure</h1><ol><li>Open a case</li><li>Check REF-1000</li></ol></body></html>",
        encoding="utf-8",
    )

    document = parse_document(path, tmp_path)

    assert document.title == "Return procedure"
    assert document.version == "2.0"
    assert document.date == "2025-09-18"
    assert document.reference == "REF-1000"
    assert document.collection == "procedures_sav"
    assert "Open a case" in document.text


def test_parse_real_pdf_extracts_text_and_filename_metadata():
    root = Path("data/corpus")
    path = root / "fiches" / "REF-8842-v1.0.pdf"
    document = parse_document(path, root)

    assert document.reference == "REF-8842"
    assert document.version == "1.0"
    assert document.doc_type == "fiche_technique"
    assert document.collection == "fiches_techniques"
    assert document.text.strip()


def test_unsupported_extension_is_explicit(tmp_path: Path):
    path = tmp_path / "document.txt"
    path.write_text("unsupported", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported document format"):
        parse_document(path, tmp_path)
