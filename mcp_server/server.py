"""Serveur MCP de la Sorabel Data Gateway — transport stdio.

Un processus = un profil = une session. Le profil est attaché au processus par
`SORABEL_PROFILE` et ne peut pas changer en cours de session : c'est ce qui
permet de filtrer le catalogue annoncé, et pas seulement les appels.

Deux barrières, volontairement redondantes :

1. `ProfiledMCP.list_tools` n'annonce que les tools autorisés au profil — un
   client honnête ne voit donc jamais un tool qu'il n'a pas le droit d'appeler ;
2. `governed()` réapplique la matrice à chaque appel — un client qui appelle un
   tool absent du catalogue est quand même refusé, avec un code typé et une
   ligne de journal.

Les descriptions remises au client viennent de `application/access_policy.json`
par `application/policy.py`. Elles ne sont pas écrites ici : c'est ce texte
qu'un agent lit pour choisir un tool, il doit rester au même endroit que les
droits qu'il décrit.
"""

from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Callable

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool as MCPTool
from pydantic import Field

from application import audit as audit_journal
from application import policy
from application.gateway import TOOLS_BY_PROFILE
from retrieval.service import build_local_service
from sql.service import build_sql_service


ROOT = Path(__file__).resolve().parent.parent
PROFILE = os.environ.get("SORABEL_PROFILE", "support")
#: Champs de version renvoyes dans le payload du service SQL.
_VERSION_KEYS = frozenset(
    {"dataset_version", "data_as_of", "semantic_schema_version", "policy_version"}
)


class ProfiledMCP(FastMCP):
    """Serveur dont le catalogue annoncé est celui du profil de la session.

    `FastMCP._setup_handlers` branche `self.list_tools` : redéfinir la méthode
    ici suffit à filtrer la réponse à `tools/list`, sans toucher au reste du
    protocole. Les tools restent tous enregistrés — donc tous appelables, donc
    tous refusables proprement par `governed()`.
    """

    def __init__(self, *args: Any, profile: str, **kwargs: Any) -> None:
        self._profile = profile
        super().__init__(*args, **kwargs)

    async def list_tools(self) -> list[MCPTool]:
        autorises = TOOLS_BY_PROFILE.get(self._profile, set())
        return [tool for tool in await super().list_tools() if tool.name in autorises]


mcp = ProfiledMCP("Sorabel Data Gateway", log_level="ERROR", profile=PROFILE)


def envelope(
    status: str,
    payload: dict | None = None,
    message: str = "",
) -> str:
    return json.dumps(
        {"status": status, "payload": payload or {}, "message": message}, ensure_ascii=False
    )


def audit(
    tool: str,
    status: str,
    request_id: str,
    result: dict | None = None,
    *,
    question: str | None = None,
    duration_ms: int | None = None,
    error_code: str | None = None,
) -> None:
    """Ecrit une ligne dans le journal partage avec l'adaptateur Web."""
    payload = (result or {}).get("payload", {})
    versions = database_service().catalog.source["versions"]
    audit_journal.write_entry(
        channel="mcp",
        tool=tool,
        status=status,
        profile=PROFILE,
        request_id=request_id,
        error_code=error_code or payload.get("error_code"),
        question=question,
        sql=payload.get("sql"),
        row_count=payload.get("row_count"),
        duration_ms=duration_ms,
        versions={**versions, **{k: v for k, v in payload.items() if k in _VERSION_KEYS}},
    )


def governed(tool: str, operation: Callable[[], dict], question: str | None = None) -> str:
    request_id = audit_journal.new_request_id()
    started = time.perf_counter()

    def elapsed() -> int:
        return int((time.perf_counter() - started) * 1000)

    if tool not in TOOLS_BY_PROFILE.get(PROFILE, set()):
        audit(
            tool,
            "refused",
            request_id,
            question=question,
            duration_ms=elapsed(),
            error_code="NOT_AUTHORIZED",
        )
        return envelope(
            "refused",
            {"error_code": "NOT_AUTHORIZED", "tool": tool, "profile": PROFILE},
            f"{tool} is not authorized for the {PROFILE} profile.",
        )
    try:
        result = operation()
        status = str(result.get("status", "ok"))
        audit(tool, status, request_id, result, question=question, duration_ms=elapsed())
        return envelope(status, result.get("payload", {}), str(result.get("message", "")))
    except (KeyError, ValueError) as exc:
        audit(tool, "refused", request_id, question=question, duration_ms=elapsed())
        return envelope("refused", message=str(exc))
    except Exception:  # noqa: BLE001
        audit(tool, "execution_error", request_id, question=question, duration_ms=elapsed())
        return envelope(
            "execution_error", message=f"Controlled execution error. request_id={request_id}"
        )


@lru_cache(maxsize=1)
def rag_service():
    return build_local_service(ROOT / "data/corpus", ROOT / "data/index")


@lru_cache(maxsize=1)
def database_service():
    return build_sql_service(ROOT)


def _rag_result(payload: dict[str, Any]) -> dict:
    return {"status": "ok", "payload": payload, "message": ""}


@mcp.tool(description=policy.describe("answer_question"))
def answer_question(question: str = "") -> str:
    def operation() -> dict:
        return rag_service().answer_question(question, PROFILE).to_envelope()

    return governed("answer_question", operation, question)


@mcp.tool(description=policy.describe("search_docs"))
def search_docs(query: str = "", limit: int = 5) -> str:
    return governed(
        "search_docs",
        lambda: _rag_result(
            {"hits": [h.to_payload() for h in rag_service().search_docs(query, PROFILE, limit)]}
        ),
        query,
    )


@mcp.tool(description=policy.describe("get_document"))
def get_document(doc_id: str = "", version: str | None = None) -> str:
    def operation() -> dict:
        document = rag_service().get_document(doc_id, PROFILE, version)
        return _rag_result(
            {
                "text": document.text,
                "metadata": document.model_dump(exclude={"text", "content_hash"}),
            }
        )

    return governed("get_document", operation)


@mcp.tool(description=policy.describe("list_sources"))
def list_sources() -> str:
    return governed(
        "list_sources",
        lambda: _rag_result(
            {
                "sources": [
                    {
                        "doc_id": d.doc_id,
                        "titre": d.title,
                        "reference": d.reference,
                        "version": d.version,
                        "date": d.date,
                        "doc_type": d.doc_type,
                    }
                    for d in rag_service().list_sources(PROFILE)
                ]
            }
        ),
    )


@mcp.tool(description=policy.describe("ask_database"))
def ask_database(question: str = "") -> str:
    return governed(
        "ask_database",
        lambda: database_service().ask_database(question, PROFILE).model_dump(mode="json"),
        question,
    )


@mcp.tool(description=policy.describe("get_schema"))
def get_schema() -> str:
    return governed(
        "get_schema",
        lambda: database_service().get_schema(PROFILE).model_dump(mode="json"),
    )


@mcp.tool(description=policy.describe("check_stock"))
def check_stock(
    reference: Annotated[
        str, Field(description="Référence produit au format REF-NNNN.", examples=["REF-8842"])
    ] = "",
    # Le format est décrit ici mais contrôlé dans le service, pas par un `pattern`
    # pydantic : mesuré le 2026-09-04, un `pattern` fait refuser l'appel au niveau
    # protocole (isError=True) — la ligne de journal n'est jamais écrite, ce qui
    # violerait E5. Tracer le refus prime sur un schéma plus riche.
) -> str:
    return governed(
        "check_stock",
        lambda: database_service().check_stock(reference, PROFILE).model_dump(mode="json"),
        reference,
    )


@mcp.tool(description=policy.describe("order_status"))
def order_status(
    order_id: Annotated[
        str,
        Field(
            description="Identifiant au format CMD-AAAA-NNNN.",
            examples=["CMD-2026-0007"],
        ),
    ] = "",
) -> str:
    return governed(
        "order_status",
        lambda: database_service().order_status(order_id, PROFILE).model_dump(mode="json"),
        order_id,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
