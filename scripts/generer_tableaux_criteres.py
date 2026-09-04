"""Écrit les tableaux de critères des documents de vérification depuis les preuves.

Pourquoi ce script existe
-------------------------
Le 2026-09-04, un ❌ écrit à la main contredisait le fichier de preuve cité dans
la même page. Le tableau des briques RAG a été généré en réponse
(`generer_tableau_briques.py`). Restaient les **tableaux de critères** des trois
documents de vérification : eux aussi recopiés, et eux aussi déjà dérivés.

Deux dérives constatées avant d'écrire ce script :

- `VERIFICATION-CHANTIER-1-RAG.md` titrait « Les **quatre** critères d'acceptance »
  au-dessus d'un tableau de **cinq** lignes, sous une sortie disant `5/5` ;
- ses durées dataient d'une exécution antérieure — 191 ms affichés contre 154 ms
  dans la preuve.

Ce que ce script génère, et ce qu'il ne génère pas
--------------------------------------------------
Il génère ce qui se **déduit** d'une mesure : le nombre de critères, la colonne
verdict, les valeurs mesurées, les durées. La colonne « Mesuré » est rendue
depuis les champs du fichier de preuve eux-mêmes, sans réécriture : c'est ce qui
rend le tableau indiscutable.

Il ne génère **pas** la prose autour — les explications, les choix d'architecture,
les limites. Celles-là restent écrites à la main, et c'est normal : ce sont des
arguments, pas des mesures.

Usage
-----
    uv run python scripts/generer_tableaux_criteres.py              # écrit
    uv run python scripts/generer_tableaux_criteres.py --verifier   # contrôle

`--verifier` sort en 1 si un document a dérivé, sans rien écrire.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREUVES = ROOT / "docs/livrable/evidence"
DOCS = ROOT / "docs/livrable"

#: Champs de structure : ils portent le tableau, pas la mesure.
META = {"critere", "question", "montre", "conforme", "duree_ms", "barriere",
        "aucune_donnee_sortie", "appel", "catalogue", "nombre", "attendu"}

#: Champs trop longs pour une cellule : on dit qu'ils existent, pas leur contenu.
TROP_LONGS = {"sql"}


def valeur(brute: Any) -> str:
    """Rend une valeur de preuve en une cellule lisible, sans l'interpréter."""
    if isinstance(brute, bool):
        return "**oui**" if brute else "**non**"
    if brute is None:
        return "*aucun*"
    if isinstance(brute, float):
        return f"**{brute:.4f}".rstrip("0").rstrip(",").replace(".", ",") + "**"
    if isinstance(brute, int):
        return f"**{brute}**"
    if isinstance(brute, list):
        return ", ".join(f"`{v}`" for v in brute) if brute else "*aucune*"
    if isinstance(brute, dict):
        # Virgule a l interieur, point median entre les champs de premier
        # niveau : sans ca, << support hits 6 · collections X · commercial >>
        # se lit comme quatre champs plats au lieu de deux groupes.
        return ", ".join(f"{c.replace(chr(95), chr(32))} {valeur(v)}" for c, v in brute.items())
    return f"`{brute}`"


def mesure(entree: dict) -> str:
    """Assemble la colonne « Mesuré » depuis les champs eux-mêmes."""
    morceaux = []
    for cle, brute in entree.items():
        if cle in META:
            continue
        if cle in TROP_LONGS:
            morceaux.append(f"{cle} **présent**" if brute else f"{cle} *absent*")
            continue
        morceaux.append(f"{cle.replace('_', ' ')} {valeur(brute)}")
    return " · ".join(morceaux) if morceaux else "—"


def note_generee(fichier: str) -> str:
    return (
        f"> Tableau **généré** par `scripts/generer_tableaux_criteres.py` depuis "
        f"`docs/livrable/evidence/{fichier}` — valeurs, verdicts et durées repris du "
        f"fichier de preuve sans réécriture. **Ne pas modifier à la main** : `--verifier` "
        f"le signalerait. Après avoir rejoué la démonstration, relancer le générateur : "
        f"les durées changent d'une exécution à l'autre, c'est normal et ce n'est pas "
        f"une dérive."
    )


# ───────────────────────────────────────────────────────── les quatre tableaux

def tableau_criteres(fichier: str, commande: str) -> str:
    """Critères d'acceptance des chantiers 1 et 2 : même forme, même preuve."""
    preuve = json.loads((PREUVES / fichier).read_text(encoding="utf-8"))
    synthese = preuve["synthese"]
    lignes = [
        "```",
        commande,
        "```",
        "",
        "```",
        f"{synthese['conformes']}/{synthese['total']} conformes",
        "```",
        "",
        "| # | Critère | Ce que ça montre | Mesuré | Conforme | Durée |",
        "|---|---|---|---|:---:|---:|",
    ]
    for entree in preuve["criteres"]:
        numero, _, titre = entree["critere"].partition(" · ")
        marque = "✅" if entree.get("conforme") else "❌"
        duree = f"{entree['duree_ms']} ms" if entree.get("duree_ms") is not None else "—"
        lignes.append(
            f"| {numero} | {titre} | {entree['montre']} | {mesure(entree)} | {marque} | {duree} |"
        )
    lignes += ["", note_generee(fichier)]
    return "\n".join(lignes)


def tableau_defense() -> str:
    """Les huit cas de défense en profondeur, barrière par barrière."""
    preuve = json.loads((PREUVES / "defense-en-profondeur.json").read_text(encoding="utf-8"))
    synthese = preuve["synthese"]
    lignes = [
        "```",
        "uv run python scripts/verifier_defense_profondeur.py",
        "```",
        "",
        "```",
        f"{synthese['contournements_arretes']}/{synthese['contournements_tentes']} "
        f"contournements arrêtés · {synthese['total']} cas · "
        f"aucune fuite : {'oui' if synthese['aucune_fuite'] else 'NON'}",
        "```",
        "",
        "| Question posée | Le mot-clé matche ? | Arrêtée par | Code | Aucune donnée sortie | Durée |",
        "|---|:---:|---|---|:---:|---:|",
    ]
    for cas in preuve["cas"]:
        matche = "oui" if cas["mot_cle_attendu"] else "**non**"
        etanche = "✅" if cas["aucune_donnee_sortie"] else "❌"
        lignes.append(
            f"| « {cas['question']} » | {matche} | {cas['barriere']} "
            f"| `{cas['error_code']}` | {etanche} | {cas['duree_ms']} ms |"
        )
    lignes += [
        "",
        "**Les lignes « non » sont celles qui comptent** : le mot-clé ne matche pas, et la "
        "question est arrêtée quand même. On ne peut pas divulguer ce qu'on n'a jamais montré "
        "au modèle.",
        "",
        note_generee("defense-en-profondeur.json"),
    ]
    return "\n".join(lignes)


def tableau_appels_mcp() -> str:
    """Le registre des appels MCP de la démonstration."""
    preuve = json.loads((PREUVES / "mcp-demonstration.json").read_text(encoding="utf-8"))
    s = preuve["synthese"]
    lignes = [
        "```",
        "uv run python scripts/demo_mcp.py",
        "```",
        "",
        "```",
        f"{s['conformes']}/{s['attendus']} conformes — {s['autorises']} autorisés, "
        f"{s['refuses']} refusés, {s['lignes_de_journal']} lignes de journal",
        "```",
        "",
        "| Profil | Appel | Ce que ça montre | Conforme | Durée |",
        "|---|---|---|:---:|---:|",
    ]
    for entree in preuve["lignes"]:
        marque = "✅" if entree.get("conforme") else "❌"
        duree = f"{entree['duree_ms']} ms" if entree.get("duree_ms") is not None else "—"
        lignes.append(
            f"| `{entree['profil']}` | `{entree['appel']}` | {entree['montre']} "
            f"| {marque} | {duree} |"
        )
    lignes += [
        "",
        f"**{s['appels']} `tools/call` pendant la démonstration → {s['lignes_de_journal']} "
        f"lignes de journal.** Tous journalisés : "
        f"{'oui' if s['tous_journalises'] else '**NON**'}. "
        f"Politique appliquée : `{preuve['policy_version']}`.",
        "",
        note_generee("mcp-demonstration.json"),
    ]
    return "\n".join(lignes)


#: (marqueur, document, fabricant)
BLOCS = (
    ("CRITERES-RAG", DOCS / "VERIFICATION-CHANTIER-1-RAG.md",
     lambda: tableau_criteres("rag-demonstration.json", "uv run python scripts/demo_rag.py")),
    ("CRITERES-SQL", DOCS / "VERIFICATION-CHANTIER-2-SQL.md",
     lambda: tableau_criteres("sql-demonstration.json", "uv run python scripts/demo_sql.py")),
    ("DEFENSE-PROFONDEUR", DOCS / "VERIFICATION-CHANTIER-2-SQL.md", tableau_defense),
    ("APPELS-MCP", DOCS / "VERIFICATION-CHANTIER-3-MCP.md", tableau_appels_mcp),
)


def appliquer(marqueur: str, document: Path, contenu: str, verifier: bool) -> str:
    debut, fin = f"<!-- {marqueur}:debut -->", f"<!-- {marqueur}:fin -->"
    if not document.exists():
        return "absent"
    texte = document.read_text(encoding="utf-8")
    if debut not in texte or fin not in texte:
        return "sans marqueurs"

    avant, reste = texte.split(debut, 1)
    _, apres = reste.split(fin, 1)
    neuf = f"{avant}{debut}\n{contenu}\n{fin}{apres}"

    if neuf == texte:
        return "a jour"
    if verifier:
        return "DERIVE"
    document.write_text(neuf, encoding="utf-8")
    return "ecrit"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier", action="store_true",
                        help="signaler une dérive sans rien écrire")
    ns = parser.parse_args()

    problemes = []
    for marqueur, document, fabriquer in BLOCS:
        etat = appliquer(marqueur, document, fabriquer(), ns.verifier)
        print(f"  {etat:<14} {marqueur:<20} {document.name}")
        if etat != "a jour" and (ns.verifier or etat in {"absent", "sans marqueurs"}):
            problemes.append(f"{marqueur} ({etat})")

    if problemes:
        print(f"\n{len(problemes)} bloc(s) à corriger : " + ", ".join(problemes))
        return 1
    print("\ntableaux de critères : les documents disent les preuves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
