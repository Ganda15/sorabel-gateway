"""Journal d'audit partagé par tous les adaptateurs d'entrée.

Le chemin MCP et le chemin Web écrivent dans le même journal, avec le même
format, afin qu'un refus soit tracé quel que soit le client utilisé.

Ce module n'écrit jamais de secret : ni identifiant de connexion, ni clé d'API,
ni jeton. Il conserve la question posée et la requête produite, car ce sont
exactement les deux éléments qu'un audit doit pouvoir rejouer.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JOURNAL = ROOT / "logs" / "journal.jsonl"
#: Une question ou une requête est tronquée au-delà de cette longueur.
MAX_TEXT_LENGTH = 500


def journal_path() -> Path:
    """Chemin du journal, relu à chaque appel pour rester testable."""
    configured = os.environ.get("GATEWAY_JOURNAL")
    return Path(configured) if configured else DEFAULT_JOURNAL


def new_request_id() -> str:
    return str(uuid.uuid4())


def _clip(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) <= MAX_TEXT_LENGTH:
        return text
    return text[:MAX_TEXT_LENGTH] + "…"


def write_entry(
    *,
    channel: str,
    tool: str,
    status: str,
    profile: str,
    request_id: str,
    error_code: str | None = None,
    question: str | None = None,
    sql: str | None = None,
    row_count: int | None = None,
    duration_ms: int | None = None,
    versions: dict[str, Any] | None = None,
) -> None:
    """Ajoute une ligne JSON au journal. Ne lève jamais : l'audit ne casse pas l'appel."""
    known = versions or {}
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "channel": channel,
        "profile": profile,
        "tool": tool,
        "status": status,
        "error_code": error_code,
        "question": _clip(question),
        "sql": _clip(sql),
        "row_count": row_count,
        "duration_ms": duration_ms,
        "dataset_version": known.get("dataset_version"),
        "data_as_of": known.get("data_as_of"),
        "semantic_schema_version": known.get("semantic_schema_version"),
        "policy_version": known.get("policy_version"),
    }
    try:
        path = journal_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        return


def read_entries(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Relit le journal. Utile aux tests et à la démonstration."""
    target = Path(path) if path is not None else journal_path()
    if not target.exists():
        return []
    return [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
