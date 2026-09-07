"""Confronte le catalogue déclaré par le contrat DSI à ce qu'un client MCP tiers voit.

Le défaut qu'il attrape : notre interface web affiche un catalogue filtré, mais
l'interface est *notre* code. Rien n'y prouve que le filtrage vit dans le serveur
MCP plutôt que dans la page. Si `ProfiledMCP.list_tools` cessait de filtrer, la
page pourrait continuer à masquer les tools et personne ne le verrait.

Méthode : on lance le **MCP Inspector**, le client de référence du protocole, sur
chaque profil, et on compare sa réponse `tools/list` à `policy.tools_by_profile()`
— la matrice déclarée dans le contrat. Aucun nombre n'est écrit ici : les deux
côtés sont lus, puis comparés. Un écart sort en 1.

On rejoue aussi la paire de démonstration de l'axe *collection* : la même question
sur deux profils, dont un seul a la note tarifaire dans son périmètre.

    uv run python scripts/verifier_client_officiel.py
    uv run python scripts/verifier_client_officiel.py --sans-preuve

Prérequis : Node (pour `npx`) et le `.venv` installé. PostgreSQL n'est pas
nécessaire : `answer_question` ne touche pas la base.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from application import policy  # noqa: E402

PREUVE = ROOT / "docs/livrable/evidence/client-officiel-mcp.json"
INSPECTEUR = ["npx", "-y", "@modelcontextprotocol/inspector", "--cli"]

#: La question de la paire de démonstration : la note tarifaire n'est dans le
#: périmètre documentaire que d'un seul des deux profils.
QUESTION = "quelle est la marge sur la REF-8842 ?"
PAIRE = {"support": "hors_corpus", "commercial": "ok"}


def lanceur(profil: str) -> Path:
    return ROOT / "scripts" / "inspecteur" / f"mcp-{profil}.cmd"


def appeler(profil: str, *arguments: str) -> dict:
    """Un aller-retour par le client officiel. `shell=True` : npx est un .cmd."""
    commande = INSPECTEUR + [str(lanceur(profil)), *arguments]
    acheve = subprocess.run(
        subprocess.list2cmdline(commande),
        shell=True, capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=ROOT, timeout=300,
    )
    sortie = acheve.stdout
    debut = sortie.find("{")
    if debut == -1:
        raise RuntimeError(f"{profil} : aucune réponse JSON\n{sortie}\n{acheve.stderr}")
    return json.loads(sortie[debut:])


def executer() -> dict:
    declare = policy.tools_by_profile()
    profils, paire = [], []

    for profil in sorted(declare):
        vus = {tool["name"] for tool in appeler(profil, "--method", "tools/list")["tools"]}
        profils.append({
            "profil": profil,
            "declare_par_le_contrat": sorted(declare[profil]),
            "vu_par_le_client_officiel": sorted(vus),
            "nombre": len(vus),
            "get_schema": "get_schema" in vus,
            "concorde": vus == declare[profil],
            "en_trop": sorted(vus - declare[profil]),
            "manquants": sorted(declare[profil] - vus),
        })

    for profil, attendu in PAIRE.items():
        brut = appeler(
            profil, "--method", "tools/call", "--tool-name", "answer_question",
            "--tool-arg", f"question={QUESTION}",
        )
        enveloppe = json.loads(brut["content"][0]["text"])
        paire.append({
            "profil": profil,
            "question": QUESTION,
            "statut": enveloppe["status"],
            "statut_attendu": attendu,
            "conforme": enveloppe["status"] == attendu,
            "sources": [s["reference"] for s in enveloppe.get("payload", {}).get("sources", [])],
        })

    return {
        "genere_le": dt.datetime.now(dt.timezone.utc).isoformat(),
        "client": "MCP Inspector (@modelcontextprotocol/inspector), transport stdio",
        "source_du_declare": "application/policy.py:tools_by_profile()",
        "catalogue": profils,
        "paire_de_demonstration": paire,
        "synthese": {
            "profils_concordants": sum(1 for p in profils if p["concorde"]),
            "profils_testes": len(profils),
            "paire_conforme": all(c["conforme"] for c in paire),
            "tout_concorde": all(p["concorde"] for p in profils)
            and all(c["conforme"] for c in paire),
        },
    }


def afficher(preuve: dict) -> None:
    print("Catalogue — contrat DSI confronté au client officiel\n")
    for p in preuve["catalogue"]:
        marque = "OK   " if p["concorde"] else "ÉCART"
        schema = "get_schema présent" if p["get_schema"] else "get_schema absent "
        print(f"{marque} {p['profil']:<11} {p['nombre']} tools · {schema}")
        if not p["concorde"]:
            print(f"        en trop : {p['en_trop']} · manquants : {p['manquants']}")

    print(f"\nPaire de démonstration — « {preuve['paire_de_demonstration'][0]['question']} »\n")
    for c in preuve["paire_de_demonstration"]:
        marque = "OK   " if c["conforme"] else "ÉCART"
        sources = ", ".join(c["sources"]) or "aucune"
        print(f"{marque} {c['profil']:<11} {c['statut']:<12} sources : {sources}")

    s = preuve["synthese"]
    print(f"\n{s['profils_concordants']}/{s['profils_testes']} profils concordants "
          f"· paire conforme : {s['paire_conforme']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sans-preuve", action="store_true")
    ns = parser.parse_args()

    preuve = executer()
    afficher(preuve)

    if not ns.sans_preuve:
        PREUVE.parent.mkdir(parents=True, exist_ok=True)
        PREUVE.write_text(json.dumps(preuve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\npreuve  {PREUVE.relative_to(ROOT).as_posix()}")

    return 0 if preuve["synthese"]["tout_concorde"] else 1
if __name__ == "__main__":
    sys.exit(main())
