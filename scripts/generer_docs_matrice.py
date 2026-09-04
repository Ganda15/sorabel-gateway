"""Régénère la documentation de la matrice d'accès depuis la politique.

La matrice était écrite à la main à quatre endroits : deux dictionnaires Python
et deux tableaux Markdown. Rien ne garantissait qu'ils disent la même chose.

Ce script rend la documentation **dérivée** : `application/access_policy.json`
fait foi, les tableaux sont réécrits entre des balises, et
`tests/unit/test_access_policy.py` échoue si un fichier a dérivé.

    uv run python scripts/generer_docs_matrice.py          # réécrit
    uv run python scripts/generer_docs_matrice.py --verifier  # ne fait que contrôler
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
# Lancé en `python scripts/…`, seul le dossier du script est sur sys.path.
sys.path.insert(0, str(ROOT))

from application import policy  # noqa: E402

#: Chaque bloc généré est délimité par ces balises, invisibles au lecteur.
DEBUT = "<!-- GENERE:{cle}:debut — ne pas éditer à la main, voir scripts/generer_docs_matrice.py -->"
FIN = "<!-- GENERE:{cle}:fin -->"

AVERTISSEMENT = (
    "> 🔒 Bloc **généré** depuis `application/access_policy.json`.\n"
    "> Le modifier ici n'a aucun effet sur le code : modifier la politique, puis relancer\n"
    "> `uv run python scripts/generer_docs_matrice.py`.\n"
)


def _coche(autorise: bool) -> str:
    return "ALLOW" if autorise else "DENY"


def table_tools() -> str:
    """Matrice profil × tool."""
    tools = policy.all_tools()
    profils = policy.profiles()
    matrice = policy.tools_by_profile()

    lignes = [
        "| Profil | " + " | ".join(f"`{t}`" for t in tools) + " |",
        "|---|" + "|".join([":---:"] * len(tools)) + "|",
    ]
    for profil in profils:
        libelle = policy.load_policy()["profils"][profil]["libelle"]
        cellules = [_coche(t in matrice[profil]) for t in tools]
        lignes.append(f"| {libelle} | " + " | ".join(cellules) + " |")
    return "\n".join(lignes)


def table_collections() -> str:
    """Matrice profil × collection documentaire."""
    politique = policy.load_policy()
    profils = policy.profiles()
    matrice = policy.collections_by_profile()

    lignes = [
        "| Collection | " + " | ".join(politique["profils"][p]["libelle"] for p in profils) + " |",
        "|---|" + "|".join([":---:"] * len(profils)) + "|",
    ]
    for nom, collection in politique["collections"].items():
        cellules = [_coche(nom in matrice[p]) for p in profils]
        lignes.append(f"| `{nom}` — {collection['libelle']} | " + " | ".join(cellules) + " |")
    return "\n".join(lignes)


def table_catalogue() -> str:
    """Contrat des huit tools : entrée, sortie, garantie, profils autorisés."""
    lignes = [
        "| Famille | Tool | Entrée | Sortie | Garantie | Profils |",
        "|---|---|---|---|---|---|",
    ]
    for spec in policy.tool_specs():
        entrees = ", ".join(f"`{k}`" for k in spec["entree"]) or "aucune"
        profils = ", ".join(spec["profils"])
        lignes.append(
            f"| {spec['famille'].upper()} | `{spec['nom']}` | {entrees} | "
            f"{spec['sortie']} | {spec['garantie']} | {profils} |"
        )
    return "\n".join(lignes)


def descriptions_tools() -> str:
    """Le texte exact que l'hôte MCP reçoit dans `tools/list`.

    C'est la seule information dont dispose un agent au moment de choisir un
    tool. Le publier tel quel évite de documenter autre chose que le réel.
    """
    blocs = []
    for spec in policy.tool_specs():
        blocs.append(f"#### `{spec['nom']}` — {spec['titre']}\n")
        blocs.append("```text")
        blocs.append(spec["description"])
        blocs.append("```\n")
    return "\n".join(blocs)


#: Ce qui est généré, et où.
BLOCS = {
    "matrice-tools": table_tools,
    "matrice-collections": table_collections,
    "catalogue-tools": table_catalogue,
    "descriptions-tools": descriptions_tools,
}


def rendre(cle: str) -> str:
    """Le bloc complet, balises et avertissement compris."""
    return "\n".join(
        [DEBUT.format(cle=cle), AVERTISSEMENT, BLOCS[cle](), FIN.format(cle=cle)]
    )


def appliquer(chemin: Path, cles: list[str], ecrire: bool) -> bool:
    """Remplace chaque bloc balisé. Renvoie True si le fichier était déjà à jour."""
    texte = chemin.read_text(encoding="utf-8")
    attendu = texte
    for cle in cles:
        motif = re.compile(
            re.escape(DEBUT.format(cle=cle)) + r".*?" + re.escape(FIN.format(cle=cle)),
            re.DOTALL,
        )
        if not motif.search(attendu):
            raise SystemExit(f"Balises manquantes pour « {cle} » dans {chemin}")
        attendu = motif.sub(lambda _m, c=cle: rendre(c), attendu, count=1)

    a_jour = attendu == texte
    if ecrire and not a_jour:
        chemin.write_text(attendu, encoding="utf-8")
    return a_jour


#: Fichier → blocs qu'il contient.
CIBLES = {
    ROOT / "docs/livrable/conception/05-matrice-acces.md": ["matrice-tools", "matrice-collections"],
    ROOT / "docs/livrable/conception/03-catalogue-tools-mcp.md": ["catalogue-tools"],
    ROOT / "docs/livrable/CATALOGUE-TOOLS-MCP.md": [
        "catalogue-tools",
        "descriptions-tools",
        "matrice-tools",
        "matrice-collections",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verifier",
        action="store_true",
        help="ne rien réécrire ; sortir en erreur si un fichier a dérivé",
    )
    ns = parser.parse_args()

    derives = []
    for chemin, cles in CIBLES.items():
        a_jour = appliquer(chemin, cles, ecrire=not ns.verifier)
        etat = "à jour" if a_jour else ("dérivé" if ns.verifier else "réécrit")
        print(f"  {etat:<8} {chemin.relative_to(ROOT).as_posix()}")
        if not a_jour:
            derives.append(chemin)

    if ns.verifier and derives:
        print(
            f"\n{len(derives)} fichier(s) ont dérivé de application/access_policy.json.\n"
            "Relancer : uv run python scripts/generer_docs_matrice.py"
        )
        return 1
    print(f"\npolitique {policy.policy_version()} — {len(policy.all_tools())} tools, "
          f"{len(policy.profiles())} profils")
    return 0


if __name__ == "__main__":
    sys.exit(main())
