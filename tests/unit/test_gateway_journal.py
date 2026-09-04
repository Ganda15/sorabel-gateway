"""Le chemin Web doit journaliser comme le chemin MCP.

Le brief impose qu'une demande d'écriture soit « refusée **et journalisée** ».
Tant que seul le serveur MCP écrivait au journal, une démonstration faite dans
le navigateur ne laissait aucune trace. Ces tests ferment ce trou.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from application import audit
from application.gateway import ApplicationGateway
from sql.models import SqlToolResult


class RefusingSqlService:
    """Refuse toute question, comme le ferait l'analyseur sur une écriture."""

    catalog = type(
        "FakeCatalog",
        (),
        {"source": {"versions": {"dataset_version": "test-v1", "data_as_of": "2026-07-31",
                                 "semantic_schema_version": "sem-v1", "policy_version": "pol-v1"}}},
    )()

    def ask_database(self, question: str, profile: str) -> SqlToolResult:
        return SqlToolResult(
            status="refused",
            payload={"error_code": "UNSAFE_SQL"},
            message="Cette demande implique une écriture et a été refusée.",
        )

    def get_schema(self, profile: str) -> SqlToolResult:
        return SqlToolResult(status="ok", payload={})

    def check_stock(self, reference: str, profile: str) -> SqlToolResult:
        return SqlToolResult(status="ok", payload={})

    def order_status(self, order_id: str, profile: str) -> SqlToolResult:
        return SqlToolResult(status="ok", payload={})


class UnusedRagService:
    def answer_question(self, question: str, profile: str):  # pragma: no cover
        raise AssertionError("le chemin RAG ne doit pas être appelé ici")

    def search_docs(self, query: str, profile: str, limit: int = 5):  # pragma: no cover
        raise AssertionError("le chemin RAG ne doit pas être appelé ici")


@pytest.fixture()
def journal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "journal.jsonl"
    monkeypatch.setenv("GATEWAY_JOURNAL", str(path))
    return path


def test_web_refusal_is_written_to_the_journal(journal: Path) -> None:
    gateway = ApplicationGateway(UnusedRagService(), RefusingSqlService())

    envelope = gateway.ask_database("supprime les commandes de test", "commercial")

    assert envelope["status"] == "refused"
    entries = audit.read_entries(journal)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["tool"] == "ask_database"
    assert entry["status"] == "refused"
    assert entry["error_code"] == "UNSAFE_SQL"
    assert entry["channel"] == "web"
    assert entry["profile"] == "commercial"


def test_journal_entry_carries_question_duration_and_versions(journal: Path) -> None:
    gateway = ApplicationGateway(UnusedRagService(), RefusingSqlService())

    gateway.ask_database("supprime les commandes de test", "commercial")

    entry = audit.read_entries(journal)[0]
    assert entry["question"] == "supprime les commandes de test"
    assert isinstance(entry["duration_ms"], int)
    assert entry["request_id"]
    assert entry["dataset_version"] == "test-v1"
    assert entry["policy_version"] == "pol-v1"


def test_tool_denied_by_the_matrix_is_also_journalised(journal: Path) -> None:
    # get_schema est DENY pour le profil support : le refus doit laisser une trace.
    gateway = ApplicationGateway(UnusedRagService(), RefusingSqlService())

    envelope = gateway.get_schema("support")

    assert envelope["status"] == "refused"
    entry = audit.read_entries(journal)[0]
    assert entry["tool"] == "get_schema"
    assert entry["profile"] == "support"


def test_long_question_is_clipped_before_being_written(journal: Path) -> None:
    gateway = ApplicationGateway(UnusedRagService(), RefusingSqlService())

    gateway.ask_database("supprime " * 400, "commercial")

    entry = audit.read_entries(journal)[0]
    assert len(entry["question"]) <= audit.MAX_TEXT_LENGTH + 1
