from __future__ import annotations

import hashlib
import re

from ingest.models import CanonicalDocument, DocumentChunk


def _split_long_block(block: str, target_chars: int, overlap_chars: int) -> list[str]:
    if len(block) <= target_chars:
        return [block]
    parts: list[str] = []
    start = 0
    while start < len(block):
        end = min(start + target_chars, len(block))
        if end < len(block):
            sentence_end = max(block.rfind(". ", start, end), block.rfind("\n", start, end))
            if sentence_end > start + target_chars // 2:
                end = sentence_end + 1
        part = block[start:end].strip()
        if part:
            parts.append(part)
        if end >= len(block):
            break
        start = max(end - overlap_chars, start + 1)
    return parts


def _blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def chunk_document(
    document: CanonicalDocument,
    target_chars: int = 650,
    overlap_chars: int = 100,
) -> list[DocumentChunk]:
    if target_chars <= 0 or overlap_chars < 0:
        raise ValueError("Chunk sizes must be positive")
    effective_overlap = min(overlap_chars, target_chars // 4)

    segments: list[str] = []
    current = ""
    for block in _blocks(document.text):
        if len(block) > target_chars:
            if current:
                segments.append(current)
                current = ""
            segments.extend(_split_long_block(block, target_chars, effective_overlap))
        elif not current:
            current = block
        elif len(current) + len(block) + 2 <= target_chars:
            current = f"{current}\n\n{block}"
        else:
            segments.append(current)
            current = block
    if current:
        segments.append(current)

    chunks: list[DocumentChunk] = []
    for index, text in enumerate(segments):
        chunk_id = hashlib.sha1(f"{document.doc_id}:{index}:{text}".encode("utf-8")).hexdigest()[:24]
        chunks.append(
            DocumentChunk(
                chunk_id=chunk_id,
                doc_id=document.doc_id,
                family_id=document.family_id,
                text=text,
                title=document.title,
                reference=document.reference,
                version=document.version,
                date=document.date,
                doc_type=document.doc_type,
                collection=document.collection,
                source_path=document.source_path,
                content_hash=document.content_hash,
                chunk_index=index,
                is_primary=document.is_primary,
            )
        )
    return chunks
