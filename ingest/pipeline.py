from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from ingest.catalog import build_catalog
from ingest.chunking import chunk_document
from ingest.models import CanonicalDocument, DocumentChunk
from ingest.parsers import parse_document


SUPPORTED_SUFFIXES = {".pdf", ".html", ".htm", ".md"}


class IngestionError(BaseModel):
    source_path: str
    message: str


class IngestionManifest(BaseModel):
    generated_at: str
    corpus_root: str
    files_seen: int
    documents_indexed: int
    duplicates_skipped: int
    families: int
    chunks_created: int
    errors: list[IngestionError] = Field(default_factory=list)


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def ingest_corpus(corpus_root: Path, output_root: Path) -> IngestionManifest:
    paths = sorted(
        path for path in corpus_root.rglob("*") if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
    )
    parsed: list[CanonicalDocument] = []
    errors: list[IngestionError] = []
    for path in paths:
        try:
            parsed.append(parse_document(path, corpus_root))
        except Exception as exc:  # noqa: BLE001
            errors.append(IngestionError(source_path=path.as_posix(), message=str(exc)))

    catalog = build_catalog(parsed)
    chunks = [chunk for document in catalog.documents for chunk in chunk_document(document)]
    manifest = IngestionManifest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        corpus_root=corpus_root.resolve().as_posix(),
        files_seen=len(paths),
        documents_indexed=len(catalog.documents),
        duplicates_skipped=catalog.stats.duplicates,
        families=catalog.stats.families,
        chunks_created=len(chunks),
        errors=errors,
    )
    _write_json_atomic(output_root / "documents.json", [item.model_dump() for item in catalog.documents])
    _write_json_atomic(output_root / "chunks.json", [item.model_dump() for item in chunks])
    _write_json_atomic(output_root / "manifest.json", manifest.model_dump())
    return manifest


def load_index(output_root: Path) -> tuple[list[CanonicalDocument], list[DocumentChunk]]:
    documents = [
        CanonicalDocument.model_validate(item)
        for item in json.loads((output_root / "documents.json").read_text(encoding="utf-8"))
    ]
    chunks = [
        DocumentChunk.model_validate(item)
        for item in json.loads((output_root / "chunks.json").read_text(encoding="utf-8"))
    ]
    return documents, chunks
