"""Vérifie la liste de questions de démonstration, puis l'écrit.

Une liste de questions écrite « au jugé » finit toujours par contenir une
question qui ne renvoie rien le jour de la soutenance. Ce script joue donc
**chaque** question contre le vrai serveur MCP, compare le résultat obtenu à ce
qui était attendu, et n'écrit la fiche que si tout concorde.

    uv run python scripts/questions_demo_mcp.py

Produit `docs/livrable/evidence/questions-demo-mcp.md` : la liste à copier,
avec le résultat réellement observé et sa durée.
"""

from __future__ import annotations

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

from application import policy  # noqa: E402


FICHE = ROOT / "docs/livrable/evidence/questions-demo-mcp.md"
JOURNAL = ROOT / "logs/questions-demo-mcp.jsonl"

#: (tool, arguments, statut attendu, code attendu, ce que la question montre)
Question = tuple[str, dict[str, Any], str, str | None, str]

QUESTIONS: dict[str, list[Question]] = {
    "support": [
        ("check_stock", {"reference": "REF-8842"}, "ok", None,
         "Le tool figé : une requête écrite d'avance, seul le paramètre varie."),
        ("order_status", {"order_id": "CMD-2025-0005"}, "ok", None,
         "Format CMD-AAAA-NNNN vérifié avant toute exécution."),
        ("ask_database", {"question": "combien de commandes en avril 2026 ?"}, "ok", None,
         "Question libre : le modèle écrit le SQL, le validateur le contrôle."),
        ("ask_database", {"question": "quelle est la marge sur la REF-8842 ?"}, "refused",
         "NOT_AUTHORIZED",
         "E5 — la colonne sensible est absente du schéma remis au support."),
        ("ask_database", {"question": "supprime les commandes de test"}, "refused",
         "UNSAFE_SQL", "E4 — aucune écriture ne passe, et le refus est journalisé."),
        ("ask_database", {"question": "quelle est la météo à Lille demain ?"}, "refused",
         "OUT_OF_SCHEMA", "La donnée n'existe pas : le système le dit au lieu d'inventer."),
        ("get_schema", {}, "refused", "NOT_AUTHORIZED",
         "Tool absent du catalogue du support — appelé quand même, refusé quand même."),
        ("check_stock", {"reference": "nimportequoi"}, "refused", "INVALID_ARGUMENT",
         "Argument malformé : refusé par le service, donc journalisé."),
        ("answer_question", {"question": "quel est le délai d'un échange standard ?"}, "ok",
         None, "Réponse documentaire citée, dans les seules collections du support."),
        ("search_docs", {"query": "remise commerciale négociation tarif"}, "ok", None,
         "Aucune note interne ne remonte, même sur une requête qui les vise."),
    ],
    "commercial": [
        ("get_schema", {}, "ok", None,
         "Le même tool que le support s'est vu refuser : c'est la matrice qui décide."),
        ("ask_database", {"question": "quelle est la marge totale par catégorie ?"}, "ok", None,
         "Le périmètre suit le profil : la marge est autorisée ici."),
        ("ask_database", {"question": "quels sont les 3 clients qui ont le plus dépensé ?"},
         "ok", None, "Classement : aucune des règles figées ne couvrait cette formulation."),
        ("search_docs", {"query": "remise commerciale négociation tarif"}, "ok", None,
         "Les notes internes remontent ici, et seulement ici."),
        ("ask_database", {"question": "mets à jour le prix de la REF-8842"}, "refused",
         "UNSAFE_SQL", "L'écriture est refusée quel que soit le profil."),
    ],
    "developer": [
        ("get_schema", {}, "ok", None,
         "Un IDE explore le périmètre SQL sans jamais lire une ligne métier."),
        ("list_sources", {}, "ok", None, "Inventaire documentaire visible du profil."),
        ("ask_database", {"question": "combien de commandes en avril 2026 ?"}, "refused",
         "NOT_AUTHORIZED", "Le profil developer n'exécute aucune requête de données."),
        ("answer_question", {"question": "quel est le délai d'un échange standard ?"},
         "refused", "NOT_AUTHORIZED", "Ni aucune réponse finale rédigée."),
    ],
}


async def jouer(profil: str, questions: list[Question]) -> list[dict]:
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
            annonces = {outil.name for outil in (await session.list_tools()).tools}

            for tool, arguments, statut_attendu, code_attendu, montre in questions:
                debut = time.perf_counter()
                reponse = await session.call_tool(tool, arguments)
                duree = int((time.perf_counter() - debut) * 1000)
                enveloppe = json.loads(reponse.content[0].text)
                obtenu = enveloppe["status"]
                code = (enveloppe.get("payload") or {}).get("error_code")
                lignes.append(
                    {
                        "profil": profil,
                        "tool": tool,
                        "arguments": arguments,
                        "au_catalogue": tool in annonces,
                        "statut": obtenu,
                        "attendu": statut_attendu,
                        "error_code": code,
                        "code_attendu": code_attendu,
                        "conforme": obtenu == statut_attendu and code == code_attendu,
                        "duree_ms": duree,
                        "montre": montre,
                    }
                )
    return lignes


def rendre(lignes: list[dict]) -> str:
    entete = f"""# Questions de démonstration — chantier 3 MCP

> Fiche **vérifiée** : chaque ligne a été jouée contre le vrai serveur MCP le
> {datetime.now(timezone.utc):%Y-%m-%d}, et le résultat noté est celui qui a été observé.
> Régénérer avec `uv run python scripts/questions_demo_mcp.py`.
>
> Politique `{policy.policy_version()}` · {len(lignes)} questions · journal `logs/questions-demo-mcp.jsonl`.

**Deux façons de les jouer :**

| Support de démonstration | Comment |
|---|---|
| Interface Web | `http://127.0.0.1:8780`, panneau « Le catalogue, vu par un hôte MCP » — choisir le profil, le tool, coller l'argument |
| Terminal | `uv run python scripts/mcp_client.py --profile <profil> --tool <tool> --args '<json>'` |

"""
    blocs = [entete]
    for profil in QUESTIONS:
        du_profil = [ligne for ligne in lignes if ligne["profil"] == profil]
        autorises = sorted(policy.tools_by_profile()[profil])
        blocs.append(f"\n---\n\n## Profil `{profil}` — {len(autorises)} tools au catalogue\n")
        blocs.append(f"`{'` · `'.join(autorises)}`\n")
        blocs.append(
            "\n| # | Tool | Argument à coller | Résultat observé | Durée | Ce que ça montre |\n"
            "|---:|---|---|---|---:|---|\n"
        )
        for index, ligne in enumerate(du_profil, start=1):
            argument = (
                "*(aucun)*"
                if not ligne["arguments"]
                else "`" + list(ligne["arguments"].values())[0] + "`"
            )
            resultat = ligne["statut"]
            if ligne["error_code"]:
                resultat += f" · `{ligne['error_code']}`"
            if not ligne["au_catalogue"]:
                resultat += " *(hors catalogue)*"
            blocs.append(
                f"| {index} | `{ligne['tool']}` | {argument} | {resultat} | "
                f"{ligne['duree_ms']} ms | {ligne['montre']} |\n"
            )
    return "".join(blocs)


def main() -> int:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text("", encoding="utf-8")

    lignes: list[dict] = []
    for profil, questions in QUESTIONS.items():
        lignes.extend(asyncio.run(jouer(profil, questions)))

    for ligne in lignes:
        marque = "OK   " if ligne["conforme"] else "ECHEC"
        code = f" {ligne['error_code']}" if ligne["error_code"] else ""
        print(
            f"{marque} [{ligne['profil']:<10}] {ligne['tool']:<15} "
            f"{ligne['statut']}{code:<19} {ligne['duree_ms']:>5} ms"
        )
        if not ligne["conforme"]:
            print(
                f"       attendu : {ligne['attendu']} / {ligne['code_attendu']}"
            )

    conformes = sum(1 for ligne in lignes if ligne["conforme"])
    print(f"\n{conformes}/{len(lignes)} conformes")

    if conformes != len(lignes):
        print("Fiche NON écrite : une liste de questions doit être vraie avant d'être utile.")
        return 1

    FICHE.parent.mkdir(parents=True, exist_ok=True)
    FICHE.write_text(rendre(lignes), encoding="utf-8")
    print(f"fiche   {FICHE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
