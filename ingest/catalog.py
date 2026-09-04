from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Iterable

from pydantic import BaseModel

from ingest.models import CanonicalDocument


def normalized_content_hash(text: str) -> str:
    normalized = " ".join(text.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def version_key(version: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", version)
    return tuple(int(number) for number in numbers) or (0,)


class CatalogStats(BaseModel):
    documents: int
    duplicates: int
    families: int
    versions: int


class DocumentCatalog(BaseModel):
    documents: list[CanonicalDocument]
    stats: CatalogStats

    def get(self, doc_id: str) -> CanonicalDocument:
        for document in self.documents:
            if document.doc_id == doc_id:
                return document
        raise KeyError(doc_id)


def build_catalog(documents: Iterable[CanonicalDocument]) -> DocumentCatalog:
    unique: list[CanonicalDocument] = []
    seen_hashes: set[str] = set()
    duplicates = 0
    for document in documents:
        digest = normalized_content_hash(document.text)
        if digest in seen_hashes:
            duplicates += 1
            continue
        seen_hashes.add(digest)
        unique.append(document.model_copy(update={"content_hash": digest, "is_primary": False}))

    families: dict[str, list[CanonicalDocument]] = defaultdict(list)
    for document in unique:
        families[document.family_id].append(document)

    resolved: list[CanonicalDocument] = []
    for family_documents in families.values():
        latest = max(family_documents, key=lambda item: (version_key(item.version), item.date, item.doc_id))
        resolved.extend(
            document.model_copy(update={"is_primary": document.doc_id == latest.doc_id})
            for document in family_documents
        )

    return DocumentCatalog(
        documents=resolved,
        stats=CatalogStats(
            documents=len(resolved),
            duplicates=duplicates,
            families=len(families),
            versions=len(resolved),
        ),
    )
