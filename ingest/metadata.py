from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ingest.models import CollectionName, DocumentType, normalize_reference


_VERSION_RE = re.compile(r"(?:^|[-_\s])v(?:ersion)?\s*([0-9]+(?:\.[0-9]+)*)", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_REFERENCE_RE = re.compile(r"\bREF[\s_-]*\d+\b", re.IGNORECASE)

_FOLDER_TYPES: dict[str, tuple[DocumentType, CollectionName]] = {
    "fiches": ("fiche_technique", "fiches_techniques"),
    "notices": ("notice", "notices"),
    "sav": ("procedure_sav", "procedures_sav"),
    "notes": ("note_interne", "notes_internes"),
}


def content_hash(text: str) -> str:
    normalized = " ".join(text.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def infer_type(path: Path) -> tuple[DocumentType, CollectionName]:
    for part in reversed(path.parts):
        if part.casefold() in _FOLDER_TYPES:
            return _FOLDER_TYPES[part.casefold()]
    raise ValueError(f"Cannot infer document type from path: {path}")


def extract_reference(*values: str) -> str:
    for value in values:
        match = _REFERENCE_RE.search(value or "")
        if match:
            return normalize_reference(match.group(0))
    return ""


def extract_version(*values: str) -> str:
    for value in values:
        match = _VERSION_RE.search(value or "")
        if match:
            return match.group(1)
    return "1.0"


def extract_date(*values: str) -> str:
    for value in values:
        match = _DATE_RE.search(value or "")
        if match:
            return match.group(1)
    return "date_unknown"


def stable_ids(path: Path, corpus_root: Path, reference: str, doc_type: str, version: str) -> tuple[str, str]:
    relative = path.resolve().relative_to(corpus_root.resolve()).as_posix()
    family_basis = f"{doc_type}:{reference or re.sub(r'-v[0-9.]+$', '', path.stem, flags=re.I)}"
    family_id = hashlib.sha1(family_basis.encode("utf-8")).hexdigest()[:16]
    doc_id = hashlib.sha1(f"{relative}:{version}".encode("utf-8")).hexdigest()[:20]
    return doc_id, family_id
