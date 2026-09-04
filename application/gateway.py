from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Protocol

from application import audit, policy
from retrieval.models import AnswerResult, SearchHit
from retrieval.service import COLLECTIONS_BY_PROFILE, build_local_service
from sql.models import SqlToolResult
from sql.service import build_sql_service


Envelope = dict[str, Any]

#: Champs de version que le service SQL renvoie dans son payload.
_VERSION_KEYS = frozenset(
    {"dataset_version", "data_as_of", "semantic_schema_version", "policy_version"}
)


class RagAnsweringService(Protocol):
    def answer_question(self, question: str, profile: str) -> AnswerResult: ...

    def search_docs(self, query: str, profile: str, limit: int = 5) -> list[SearchHit]: ...


class SqlAnsweringService(Protocol):
    def ask_database(self, question: str, profile: str) -> SqlToolResult: ...

    def get_schema(self, profile: str) -> SqlToolResult: ...

    def check_stock(self, reference: str, profile: str) -> SqlToolResult: ...

    def order_status(self, order_id: str, profile: str) -> SqlToolResult: ...


#: Axe *tool* de la matrice d'acces, lu dans application/access_policy.json.
#: Ce dictionnaire n'est plus ecrit a la main : la politique fait foi, et
#: scripts/generer_docs_matrice.py regenere la documentation depuis la meme
#: source. Voir application/policy.py.
TOOLS_BY_PROFILE = policy.tools_by_profile()


class ApplicationGateway:
    """Protocol-neutral entry point shared by web, MCP and future clients."""

    def __init__(
        self,
        rag_service: RagAnsweringService,
        sql_service: SqlAnsweringService | None = None,
    ):
        self.rag_service = rag_service
        self.sql_service = sql_service

    @staticmethod
    def _authorize(tool: str, profile: str) -> Envelope | None:
        if profile not in TOOLS_BY_PROFILE:
            return {
                "status": "invalid_request",
                "payload": {},
                "message": "Unknown profile.",
            }
        if tool not in TOOLS_BY_PROFILE[profile]:
            return {
                "status": "refused",
                "payload": {},
                "message": f"{tool} is not authorized for the {profile} profile.",
            }
        return None

    def _versions(self) -> dict[str, Any]:
        catalog = getattr(self.sql_service, "catalog", None)
        source = getattr(catalog, "source", None)
        if isinstance(source, dict):
            versions = source.get("versions")
            if isinstance(versions, dict):
                return versions
        return {}

    def _journal(
        self,
        *,
        tool: str,
        profile: str,
        envelope: Envelope,
        question: str | None,
        started: float,
    ) -> Envelope:
        """Trace l'appel — autorisé, refusé ou en erreur — puis renvoie l'enveloppe."""
        payload = envelope.get("payload") or {}
        audit.write_entry(
            channel="web",
            tool=tool,
            status=str(envelope.get("status", "execution_error")),
            profile=profile,
            request_id=audit.new_request_id(),
            error_code=payload.get("error_code"),
            question=question,
            sql=payload.get("sql"),
            row_count=payload.get("row_count"),
            duration_ms=int((time.perf_counter() - started) * 1000),
            versions={**self._versions(), **{k: v for k, v in payload.items() if k in _VERSION_KEYS}},
        )
        return envelope

    def _sql_call(self, tool: str, profile: str, *args: str) -> Envelope:
        started = time.perf_counter()
        question = args[0] if args else None
        refusal = self._authorize(tool, profile)
        if refusal is not None:
            return self._journal(
                tool=tool, profile=profile, envelope=refusal, question=question, started=started
            )
        if self.sql_service is None:
            envelope: Envelope = {
                "status": "execution_error",
                "payload": {},
                "message": "The SQL service is not configured.",
            }
            return self._journal(
                tool=tool, profile=profile, envelope=envelope, question=question, started=started
            )
        try:
            operation = getattr(self.sql_service, tool)
            result: SqlToolResult = operation(*args, profile)
            return self._journal(
                tool=tool,
                profile=profile,
                envelope=result.model_dump(mode="json"),
                question=question,
                started=started,
            )
        except Exception:  # noqa: BLE001
            envelope = {
                "status": "execution_error",
                "payload": {},
                "message": "The SQL service could not process this request.",
            }
            return self._journal(
                tool=tool, profile=profile, envelope=envelope, question=question, started=started
            )

    def answer_question(self, question: str, profile: str) -> Envelope:
        started = time.perf_counter()

        def traced(envelope: Envelope) -> Envelope:
            return self._journal(
                tool="answer_question",
                profile=profile,
                envelope=envelope,
                question=question,
                started=started,
            )

        if not question.strip():
            return traced(
                {
                    "status": "invalid_request",
                    "payload": {},
                    "message": "Question must not be empty.",
                }
            )
        if profile not in COLLECTIONS_BY_PROFILE:
            return traced(
                {"status": "invalid_request", "payload": {}, "message": "Unknown profile."}
            )
        if "answer_question" not in TOOLS_BY_PROFILE[profile]:
            return traced(
                {
                    "status": "refused",
                    "payload": {},
                    "message": f"answer_question is not authorized for the {profile} profile.",
                }
            )
        try:
            return traced(self.rag_service.answer_question(question, profile).to_envelope())
        except Exception:  # noqa: BLE001
            return traced(
                {
                    "status": "execution_error",
                    "payload": {},
                    "message": "The RAG service could not process this request.",
                }
            )

    def search_docs(self, query: str, profile: str, limit: int = 5) -> Envelope:
        started = time.perf_counter()

        def traced(envelope: Envelope) -> Envelope:
            return self._journal(
                tool="search_docs",
                profile=profile,
                envelope=envelope,
                question=query,
                started=started,
            )

        if not query.strip():
            return traced(
                {
                    "status": "invalid_request",
                    "payload": {},
                    "message": "Search query must not be empty.",
                }
            )
        if profile not in COLLECTIONS_BY_PROFILE:
            return traced(
                {"status": "invalid_request", "payload": {}, "message": "Unknown profile."}
            )
        if "search_docs" not in TOOLS_BY_PROFILE[profile]:
            return traced(
                {
                    "status": "refused",
                    "payload": {},
                    "message": f"search_docs is not authorized for the {profile} profile.",
                }
            )
        try:
            hits = self.rag_service.search_docs(query, profile, limit)
            return traced(
                {
                    "status": "ok",
                    "payload": {"hits": [hit.to_payload() for hit in hits]},
                    "message": "",
                }
            )
        except Exception:  # noqa: BLE001
            return traced(
                {
                    "status": "execution_error",
                    "payload": {},
                    "message": "The RAG service could not process this request.",
                }
            )

    def ask_database(self, question: str, profile: str) -> Envelope:
        if not question.strip():
            return {
                "status": "invalid_request",
                "payload": {},
                "message": "Question must not be empty.",
            }
        return self._sql_call("ask_database", profile, question)

    def get_schema(self, profile: str) -> Envelope:
        return self._sql_call("get_schema", profile)

    def check_stock(self, reference: str, profile: str) -> Envelope:
        return self._sql_call("check_stock", profile, reference)

    def order_status(self, order_id: str, profile: str) -> Envelope:
        return self._sql_call("order_status", profile, order_id)


def build_application_gateway(root: Path) -> ApplicationGateway:
    rag_service = build_local_service(root / "data/corpus", root / "data/index")
    sql_service = build_sql_service(root)
    return ApplicationGateway(rag_service, sql_service)
