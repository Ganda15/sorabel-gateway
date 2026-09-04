import json
from pathlib import Path

from ingest.pipeline import ingest_corpus, load_index


def test_pipeline_builds_manifest_and_loadable_index(tmp_path: Path):
    corpus = tmp_path / "corpus"
    note = corpus / "notes" / "note-2026-01-01.md"
    procedure = corpus / "sav" / "procedure-v2.0.html"
    note.parent.mkdir(parents=True)
    procedure.parent.mkdir(parents=True)
    note.write_text(
        "---\ntitre: Note\ndate: 2026-01-01\ntype: note_interne\nversion: 1.0\n---\n# Note\nREF-8842 checked.",
        encoding="utf-8",
    )
    procedure.write_text(
        '<html><head><title>Return</title><meta name="version" content="2.0">'
        '<meta name="date" content="2025-01-01"></head><body>Open a return case.</body></html>',
        encoding="utf-8",
    )
    output = tmp_path / "index"

    manifest = ingest_corpus(corpus, output)
    documents, chunks = load_index(output)

    assert manifest.files_seen == 2
    assert manifest.documents_indexed == 2
    assert manifest.chunks_created == len(chunks)
    assert len(documents) == 2
    assert (output / "manifest.json").exists()
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8"))["errors"] == []
