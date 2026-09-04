from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ingest.metadata import (
    content_hash,
    extract_date,
    extract_reference,
    extract_version,
    infer_type,
    stable_ids,
)
from ingest.models import CanonicalDocument


def _build_document(
    path: Path,
    corpus_root: Path,
    text: str,
    title: str,
    metadata: dict[str, str] | None = None,
) -> CanonicalDocument:
    if not text.strip():
        raise ValueError(f"No readable text extracted from: {path}")
    metadata = metadata or {}
    doc_type, collection = infer_type(path)
    reference = extract_reference(metadata.get("reference", ""), path.name, text)
    version = metadata.get("version") or extract_version(path.stem, text)
    date = metadata.get("date") or extract_date(path.stem, text)
    doc_id, family_id = stable_ids(path, corpus_root, reference, doc_type, version)
    return CanonicalDocument(
        doc_id=doc_id,
        family_id=family_id,
        title=title.strip() or path.stem,
        reference=reference,
        version=version.strip(" '\""),
        date=date,
        doc_type=doc_type,
        collection=collection,
        source_path=path.resolve().relative_to(corpus_root.resolve()).as_posix(),
        content_hash=content_hash(text),
        text=text.strip(),
    )


def parse_pdf(path: Path, corpus_root: Path) -> CanonicalDocument:
    try:
        reader = PdfReader(path)
        text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Unable to parse PDF {path}: {exc}") from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else path.stem
    return _build_document(path, corpus_root, text, title)


def parse_html(path: Path, corpus_root: Path) -> CanonicalDocument:
    try:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Unable to parse HTML {path}: {exc}") from exc
    metadata: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        name = tag.get("name")
        content = tag.get("content")
        if isinstance(name, str) and isinstance(content, str):
            metadata[name.casefold()] = content
    title = (soup.title.string if soup.title and soup.title.string else "") or path.stem
    text = soup.body.get_text("\n", strip=True) if soup.body else soup.get_text("\n", strip=True)
    return _build_document(path, corpus_root, text, title, metadata)


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", raw, re.DOTALL)
    if not match:
        return {}, raw
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip().casefold()] = value.strip().strip("'\"")
    return metadata, raw[match.end() :]


def parse_markdown(path: Path, corpus_root: Path) -> CanonicalDocument:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Unable to parse Markdown {path}: {exc}") from exc
    metadata, body = _parse_front_matter(raw)
    heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = metadata.get("titre") or metadata.get("title") or (heading.group(1) if heading else path.stem)
    return _build_document(path, corpus_root, body, title, metadata)


def parse_document(path: Path, corpus_root: Path) -> CanonicalDocument:
    parsers = {".pdf": parse_pdf, ".html": parse_html, ".htm": parse_html, ".md": parse_markdown}
    parser = parsers.get(path.suffix.casefold())
    if parser is None:
        raise ValueError(f"Unsupported document format: {path.suffix or '<none>'} ({path})")
    return parser(path, corpus_root)
