"""Démonstration RAG avancé — chantier 1, les quatre critères d'acceptance.

Rejoue, en une commande, ce que le brief exige du chantier 1 :

1. une question couverte reçoit une réponse **sourcée** — titre, référence, date ;
2. une question hors corpus est signalée, **sans fabrication** ;
3. « REF-8842 » fait remonter la fiche technique **en tête** ;
4. la recherche hybride **surpasse** la dense, gain mesuré, pas recopié.

Un cinquième contrôle s'ajoute, qui n'est pas dans le brief mais que le jury
demandera : le périmètre documentaire du profil support exclut vraiment les
notes internes.

Les appels passent par le **vrai serveur MCP**, comme `scripts/demo_mcp.py` : ce
qui est démontré est ce qu'un client externe obtient, pas ce qu'une fonction
interne renvoie.

    uv run python scripts/demo_rag.py

Produit `docs/livrable/evidence/rag-demonstration.json`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from retrieval.evaluation import evaluate_retrieval  # noqa: E402
from retrieval.service import build_local_service  # noqa: E402


PREUVE = ROOT / "docs/livrable/evidence/rag-demonstration.json"
JOURNAL = ROOT / "logs/demonstration-rag.jsonl"

QUESTION_COUVERTE = "quelle est la procédure de retour d'un produit défectueux sous garantie ?"
QUESTION_HORS_CORPUS = "quelle est la politique de télétravail chez Sorabel ?"
REQUETE_NOTES_INTERNES = "remise commerciale négociation tarif"


def _session(profil: str) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env={**os.environ, "SORABEL_PROFILE": profil, "GATEWAY_JOURNAL": str(JOURNAL)},
        cwd=str(ROOT),
    )


async def _appeler(session: ClientSession, tool: str, arguments: dict) -> tuple[dict, int]:
    debut = time.perf_counter()
    reponse = await session.call_tool(tool, arguments)
    duree = int((time.perf_counter() - debut) * 1000)
    return json.loads(reponse.content[0].text), duree


async def criteres_mcp() -> list[dict[str, Any]]:
    """Les critères qui passent par le protocole : 1, 2, 3 et le périmètre."""
    lignes: list[dict[str, Any]] = []

    async with stdio_client(_session("support")) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # --- Critère 1 : réponse sourcée ---
            enveloppe, duree = await _appeler(
                session, "answer_question", {"question": QUESTION_COUVERTE}
            )
            payload = enveloppe.get("payload") or {}
            sources = payload.get("sources") or []
            complet = bool(sources) and all(
                (s.get("titre") or "").strip()
                and (s.get("reference") or "").strip()
                and (s.get("date") or "").strip()
                for s in sources
            )
            lignes.append({
                "critere": "1 · réponse sourcée",
                "question": QUESTION_COUVERTE,
                "statut": enveloppe.get("status"),
                "attendu": "ok",
                "sources": len(sources),
                "titre_reference_date_complets": complet,
                "conforme": enveloppe.get("status") == "ok" and complet,
                "duree_ms": duree,
                "montre": "E1 — chaque source porte son titre, sa référence et sa date.",
            })

            # --- Critère 2 : hors corpus, sans invention ---
            enveloppe, duree = await _appeler(
                session, "answer_question", {"question": QUESTION_HORS_CORPUS}
            )
            payload = enveloppe.get("payload") or {}
            lignes.append({
                "critere": "2 · hors corpus sans fabrication",
                "question": QUESTION_HORS_CORPUS,
                "statut": enveloppe.get("status"),
                "attendu": "hors_corpus",
                "reponse_fabriquee": bool(payload.get("answer")),
                "conforme": enveloppe.get("status") == "hors_corpus"
                and not payload.get("answer"),
                "duree_ms": duree,
                "montre": "E1 — le système dit qu'il ne sait pas plutôt que d'inventer.",
            })

            # --- Critère 3 : la référence exacte remonte en tête ---
            enveloppe, duree = await _appeler(session, "search_docs", {"query": "REF-8842"})
            hits = (enveloppe.get("payload") or {}).get("hits") or []
            tete = (hits[0].get("metadata") if hits else {}) or {}
            lignes.append({
                "critere": "3 · REF-8842 en tête",
                "question": "REF-8842",
                "statut": enveloppe.get("status"),
                "attendu": "ok",
                "reference_en_tete": tete.get("reference"),
                "type_en_tete": tete.get("doc_type"),
                "conforme": enveloppe.get("status") == "ok"
                and tete.get("reference") == "REF-8842"
                and tete.get("doc_type") == "fiche_technique",
                "duree_ms": duree,
                "montre": "E2 — une référence exacte n'est pas noyée par la similarité.",
            })

    return lignes


def critere_perimetre() -> dict[str, Any]:
    """Critère 5 : le périmètre documentaire, mesuré **côté service**.

    Il ne peut pas passer par MCP : le contrat `search_docs` de la DSI n'expose
    pas la collection d'un passage — seulement doc_id, score, texte, référence,
    type, version et date. Le lire dans le payload reviendrait à lire un champ
    absent et à conclure « aucune note interne » sans rien avoir vérifié.
    C'était le cas dans la première version de ce script.
    """
    debut = time.perf_counter()
    service = build_local_service(ROOT / "data/corpus", ROOT / "data/index")

    mesures = {}
    for profil in ("support", "commercial"):
        hits = service.search_docs(REQUETE_NOTES_INTERNES, profil, limit=10)
        mesures[profil] = {
            "hits": len(hits),
            "collections": sorted({hit.collection for hit in hits}),
        }

    support = mesures["support"]
    commercial = mesures["commercial"]
    return {
        "critere": "5 · périmètre documentaire du support",
        "question": REQUETE_NOTES_INTERNES,
        "mesure_par": "service direct — le contrat search_docs n'expose pas la collection",
        "support": support,
        "commercial": commercial,
        # Deux conditions : le support n'en voit aucune, ET le commercial en voit,
        # sinon un corpus vide ferait passer le test pour de mauvaises raisons.
        "conforme": "notes_internes" not in support["collections"]
        and support["hits"] > 0
        and "notes_internes" in commercial["collections"],
        "duree_ms": int((time.perf_counter() - debut) * 1000),
        "montre": "La requête vise les notes internes : zéro pour le support, présentes pour le commercial.",
    }


def critere_gain() -> dict[str, Any]:
    """Critère 4 : le gain hybride, **remesuré**, pas relu dans le rapport."""
    debut = time.perf_counter()
    questions = [
        json.loads(ligne)
        for ligne in (ROOT / "eval/questions_rag.jsonl").read_text(encoding="utf-8").splitlines()
        if ligne.strip()
    ]
    service = build_local_service(ROOT / "data/corpus", ROOT / "data/index")
    dense = evaluate_retrieval(service, questions, "dense")
    hybride = evaluate_retrieval(service, questions, "hybrid")
    gain = round(hybride.recall_at_1 - dense.recall_at_1, 4)

    return {
        "critere": "4 · hybride > dense, mesuré",
        # `evaluate_retrieval` saute les questions hors corpus : le nombre qui
        # compte est celui qu'il a réellement évaluées, pas les lignes du fichier.
        "questions_du_fichier": len(questions),
        "questions_evaluees": dense.total,
        "dense_recall_at_1": round(dense.recall_at_1, 4),
        "hybride_recall_at_1": round(hybride.recall_at_1, 4),
        "gain_absolu_points": round(gain * 100, 1),
        "dense_mrr": round(dense.mrr, 4),
        "hybride_mrr": round(hybride.mrr, 4),
        "conforme": hybride.recall_at_1 > dense.recall_at_1,
        "duree_ms": int((time.perf_counter() - debut) * 1000),
        "montre": "E6 — le gain est recalculé à chaque exécution, jamais recopié.",
    }


def afficher(preuve: dict) -> None:
    for ligne in preuve["criteres"]:
        marque = "OK   " if ligne["conforme"] else "ECHEC"
        print(f"{marque} {ligne['critere']:<42} {ligne['duree_ms']:>6} ms")
        print(f"        {ligne['montre']}")
        if "gain_absolu_points" in ligne:
            print(f"        dense {ligne['dense_recall_at_1']} → hybride "
                  f"{ligne['hybride_recall_at_1']}  (+{ligne['gain_absolu_points']} points, "
                  f"{ligne['questions_evaluees']} questions)")
        elif "support" in ligne:
            print(f"        support : {ligne['support']['hits']} hits "
                  f"{ligne['support']['collections']}")
            print(f"        commercial : {ligne['commercial']['hits']} hits "
                  f"{ligne['commercial']['collections']}")
        elif "sources" in ligne:
            print(f"        {ligne['sources']} source(s), toutes complètes : "
                  f"{ligne['titre_reference_date_complets']}")
        elif "reference_en_tete" in ligne:
            print(f"        en tête : {ligne['reference_en_tete']} · {ligne['type_en_tete']}")

    s = preuve["synthese"]
    print(f"\n{s['conformes']}/{s['total']} conformes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sans-preuve", action="store_true")
    ns = parser.parse_args()

    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text("", encoding="utf-8")

    criteres = asyncio.run(criteres_mcp())
    criteres.append(critere_gain())
    criteres.append(critere_perimetre())

    preuve = {
        "genere_le": datetime.now(timezone.utc).isoformat(),
        "journal": JOURNAL.relative_to(ROOT).as_posix(),
        "criteres": criteres,
        "synthese": {
            "total": len(criteres),
            "conformes": sum(1 for c in criteres if c["conforme"]),
        },
    }
    afficher(preuve)

    if not ns.sans_preuve:
        PREUVE.parent.mkdir(parents=True, exist_ok=True)
        PREUVE.write_text(json.dumps(preuve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\npreuve  {PREUVE.relative_to(ROOT).as_posix()}")

    return 0 if preuve["synthese"]["conformes"] == preuve["synthese"]["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
