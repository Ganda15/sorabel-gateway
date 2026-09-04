"""Démonstration MCP deux profils — support contre commercial.

Rejoue, en une commande, les quatre critères d'acceptance du chantier 3 :

1. un client autorisé n'accède qu'aux tools de la matrice ;
2. un client non autorisé est refusé avec un message clair, et journalisé ;
3. les briques du RAG fonctionnent séparément — `search_docs` puis `get_document` ;
4. le journal contient **tous** les appels, autorisés comme refusés.

Produit deux preuves relisibles :

* `docs/livrable/evidence/mcp-demonstration.json` — la session complète ;
* `logs/demonstration-mcp.jsonl` — le journal d'audit de cette session.

    uv run python scripts/demo_mcp.py
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
# Lancé en `python scripts/…`, seul le dossier du script est sur sys.path.
sys.path.insert(0, str(ROOT))

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from application import audit, policy  # noqa: E402


PREUVE = ROOT / "docs/livrable/evidence/mcp-demonstration.json"
JOURNAL = ROOT / "logs/demonstration-mcp.jsonl"

#: Scénario joué pour chaque profil. `attendu` sert de contrôle, pas de décor :
#: le script sort en erreur si la réalité en diffère.
SCENARIO: list[dict[str, Any]] = [
    {
        "profil": "support",
        "tool": "get_schema",
        "args": {},
        "attendu": "refused",
        "montre": "Critère 2 — un tool hors matrice est refusé, proprement et par écrit.",
    },
    {
        "profil": "commercial",
        "tool": "get_schema",
        "args": {},
        "attendu": "ok",
        "montre": "Le même tool, un autre profil : c'est la matrice qui décide, pas le code du tool.",
    },
    {
        "profil": "support",
        "tool": "search_docs",
        "args": {"query": "retour d'un produit défectueux sous garantie"},
        "attendu": "ok",
        "montre": "Critère 3 — chercher sans générer : la première brique du RAG, seule.",
    },
    {
        "profil": "support",
        "tool": "get_document",
        "args": {"doc_id": "@search_docs.hits[0].doc_id"},
        "attendu": "ok",
        "montre": "Critère 3 — lire le document trouvé : la seconde brique, enchaînée à la main.",
    },
    {
        "profil": "support",
        "tool": "ask_database",
        "args": {"question": "quelle est la marge sur la REF-8842 ?"},
        "attendu": "refused",
        "montre": "E5 — aucune colonne sensible ne sort pour le support.",
    },
    {
        "profil": "commercial",
        "tool": "ask_database",
        "args": {"question": "quelle est la marge totale par catégorie ?"},
        "attendu": "ok",
        "montre": "La même donnée, autorisée au commercial : le périmètre suit le profil.",
    },
    {
        "profil": "support",
        "tool": "ask_database",
        "args": {"question": "supprime les commandes de test"},
        "attendu": "refused",
        "montre": "E4 — aucune écriture ne passe, et le refus est daté au journal.",
    },
    {
        "profil": "support",
        "tool": "check_stock",
        "args": {"reference": "REF-8842"},
        "attendu": "ok",
        "montre": "Un tool figé : requête écrite d'avance, seul le paramètre varie.",
    },
]


def _resoudre(valeur: Any, resultats: dict[str, Any]) -> Any:
    """Remplace `@search_docs.hits[0].doc_id` par la valeur réellement obtenue.

    Un identifiant écrit en dur dans un scénario finit par mentir. Ici la
    seconde brique du RAG consomme vraiment la sortie de la première.
    """
    if not (isinstance(valeur, str) and valeur.startswith("@")):
        return valeur
    tool, _, chemin = valeur[1:].partition(".")
    courant = resultats[tool]["payload"]
    for morceau in chemin.replace("]", "").split("."):
        if "[" in morceau:
            nom, _, index = morceau.partition("[")
            courant = courant[nom][int(index)]
        else:
            courant = courant[morceau]
    return courant


async def _session(profil: str, etapes: list[dict], resultats: dict) -> list[dict]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        env={**os.environ, "SORABEL_PROFILE": profil, "GATEWAY_JOURNAL": str(JOURNAL)},
        cwd=str(ROOT),
    )
    lignes = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            catalogue = [t.name for t in listed.tools]
            lignes.append(
                {
                    "profil": profil,
                    "appel": "tools/list",
                    "catalogue": catalogue,
                    "nombre": len(catalogue),
                    "attendu": sorted(policy.tools_by_profile()[profil]),
                    "conforme": set(catalogue) == policy.tools_by_profile()[profil],
                    "montre": "Critère 1 — le catalogue annoncé est celui de la matrice.",
                }
            )

            for etape in etapes:
                args = {k: _resoudre(v, resultats) for k, v in etape["args"].items()}
                debut = time.perf_counter()
                reponse = await session.call_tool(etape["tool"], args)
                duree = int((time.perf_counter() - debut) * 1000)
                enveloppe = json.loads(reponse.content[0].text)
                resultats[etape["tool"]] = enveloppe
                lignes.append(
                    {
                        "profil": profil,
                        "appel": "tools/call",
                        "tool": etape["tool"],
                        "arguments": args,
                        "statut": enveloppe["status"],
                        "attendu": etape["attendu"],
                        "conforme": enveloppe["status"] == etape["attendu"],
                        "error_code": (enveloppe.get("payload") or {}).get("error_code"),
                        "message": enveloppe.get("message", ""),
                        "duree_ms": duree,
                        "montre": etape["montre"],
                    }
                )
    return lignes


async def demontrer() -> dict:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text("", encoding="utf-8")

    resultats: dict[str, Any] = {}
    lignes: list[dict] = []
    # Une session par profil, dans l'ordre du scénario : le profil est attaché
    # au processus, il ne peut pas changer en cours de session.
    for profil in ("support", "commercial"):
        etapes = [e for e in SCENARIO if e["profil"] == profil]
        lignes.extend(await _session(profil, etapes, resultats))

    entrees = audit.read_entries(JOURNAL)
    appels = [ligne for ligne in lignes if ligne["appel"] == "tools/call"]
    return {
        "genere_le": datetime.now(timezone.utc).isoformat(),
        "policy_version": policy.policy_version(),
        "journal": JOURNAL.relative_to(ROOT).as_posix(),
        "lignes": lignes,
        "synthese": {
            "appels": len(appels),
            "conformes": sum(1 for ligne in lignes if ligne["conforme"]),
            "attendus": len(lignes),
            "autorises": sum(1 for a in appels if a["statut"] == "ok"),
            "refuses": sum(1 for a in appels if a["statut"] == "refused"),
            "lignes_de_journal": len(entrees),
            "tous_journalises": len(entrees) == len(appels),
        },
    }


def afficher(preuve: dict) -> None:
    for ligne in preuve["lignes"]:
        marque = "OK  " if ligne["conforme"] else "ECHEC"
        if ligne["appel"] == "tools/list":
            print(f"{marque} [{ligne['profil']:<10}] tools/list -> {ligne['nombre']} tools")
            print(f"      {', '.join(ligne['catalogue'])}")
        else:
            code = f" {ligne['error_code']}" if ligne["error_code"] else ""
            print(
                f"{marque} [{ligne['profil']:<10}] {ligne['tool']:<14} "
                f"{ligne['statut']}{code}  {ligne['duree_ms']} ms"
            )
        print(f"      {ligne['montre']}")

    s = preuve["synthese"]
    print(
        f"\n{s['conformes']}/{s['attendus']} conformes — "
        f"{s['autorises']} autorisés, {s['refuses']} refusés, "
        f"{s['lignes_de_journal']} lignes de journal"
    )
    if not s["tous_journalises"]:
        print("ATTENTION — des appels manquent au journal.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sans-preuve", action="store_true", help="afficher sans écrire le fichier de preuve"
    )
    ns = parser.parse_args()

    preuve = asyncio.run(demontrer())
    afficher(preuve)

    if not ns.sans_preuve:
        PREUVE.parent.mkdir(parents=True, exist_ok=True)
        PREUVE.write_text(
            json.dumps(preuve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\npreuve  {PREUVE.relative_to(ROOT).as_posix()}")
        print(f"journal {JOURNAL.relative_to(ROOT).as_posix()}")

    s = preuve["synthese"]
    return 0 if s["conformes"] == s["attendus"] and s["tous_journalises"] else 1


if __name__ == "__main__":
    sys.exit(main())
