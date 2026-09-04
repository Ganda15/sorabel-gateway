from __future__ import annotations

import re
import unicodedata


_REFERENCE_WITH_SPACE = re.compile(r"\bref[\s_-]+(\d+)\b", re.IGNORECASE)
_TOKEN_RE = re.compile(r"ref-\d+|[a-z0-9]+", re.IGNORECASE)
_STOP_WORDS = {
    "a", "au", "aux", "avec", "ce", "ces", "chez", "dans", "de", "des", "du", "en", "est",
    "et", "faire", "la", "le", "les", "pour", "que", "quel", "quelle", "qui", "sorabel", "sur", "un", "une",
}


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = _REFERENCE_WITH_SPACE.sub(r"ref-\1", normalized)
    return [token for token in _TOKEN_RE.findall(normalized) if token not in _STOP_WORDS]
