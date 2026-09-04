import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


DocumentType = Literal[
    "fiche_technique",
    "notice",
    "procedure_sav",
    "note_interne",
]

CollectionName = Literal[
    "fiches_techniques",
    "notices",
    "procedures_sav",
    "notes_internes",
]

_REFERENCE_PATTERN = re.compile(r"\bREF[\s_-]*(\d+)\b", re.IGNORECASE)


def normalize_reference(value: str | None) -> str:
    """Return a product reference in the canonical REF-1234 format."""
    if value is None:
        return ""

    cleaned = value.strip()
    match = _REFERENCE_PATTERN.search(cleaned)

    if match is None:
        return cleaned.upper()

    return f"REF-{match.group(1)}"


class CanonicalDocument(BaseModel):
    """Normalized document produced before chunking and indexing."""

    model_config = ConfigDict(str_strip_whitespace=True)

    doc_id: str
    family_id: str
    title: str
    reference: str = ""
    version: str
    date: str
    doc_type: DocumentType
    collection: CollectionName
    source_path: str
    content_hash: str
    text: str
    is_primary: bool = True

    @field_validator("reference", mode="before")
    @classmethod
    def normalize_product_reference(cls, value: str | None) -> str:
        return normalize_reference(value)

class DocumentChunk(BaseModel):
    """Searchable passage that preserves its document metadata."""

    model_config = ConfigDict(str_strip_whitespace=True)

    chunk_id: str
    doc_id: str
    family_id: str
    text: str
    title: str
    reference: str = ""
    version: str
    date: str
    doc_type: DocumentType
    collection: CollectionName
    source_path: str
    content_hash: str
    chunk_index: int
    is_primary: bool = True

    @field_validator("reference", mode="before")
    @classmethod
    def normalize_product_reference(cls, value: str | None) -> str:
        return normalize_reference(value)   