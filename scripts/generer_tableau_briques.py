"""Ecrit le tableau de comparaison des briques RAG depuis le fichier de preuve.

Pourquoi ce script existe
-------------------------
Le tableau des quatre configurations etait recopie a la main dans trois
documents. Le 2026-09-04, il y portait une croix rouge sur `chroma + lexical`
alors que le fichier de preuve cite juste a cote disait `reproductible: true`
pour les quatre configurations. Trois documents affirmaient donc le contraire
de la mesure qu'ils citaient.

Un tableau recopie derive. Celui-ci est genere : il ne peut plus dire autre
chose que `docs/livrable/evidence/comparaison-briques-rag.json`.

Usage
-----
    uv run python scripts/generer_tableau_briques.py              # ecrit
    uv run python scripts/generer_tableau_briques.py --verifier   # controle

`--verifier` sort en 1 si un document a derive, sans rien ecrire. C'est la
commande a passer avant une remise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREUVE = ROOT / "docs/livrable/evidence/comparaison-briques-rag.json"

DEBUT = "<!-- TABLEAU-BRIQUES:debut -->"
FIN = "<!-- TABLEAU-BRIQUES:fin -->"

#: Les documents qui portent le tableau. Chemins relatifs a la racine du projet
#: Sorabel (un cran au-dessus du depot), car deux d'entre eux vivent dans le
#: dossier de remise et non dans le depot.
DOCUMENTS = (
    ROOT / "docs/livrable/VERIFICATION-CHANTIER-1-RAG.md",
    ROOT.parent.parent / "SORABEL-LIVRABLE/LIRE-EN-PREMIER.md",
    ROOT.parent.parent / "SORABEL-LIVRABLE/CONFORMITE-BRIEF.md",
)

#: Ce qu'on affiche pour chaque configuration, dans l'ordre du tableau.
LIBELLES = {
    ("local", "identity"): "local, sans reranking",
    ("local", "lexical"): "**local + reranking lexical** *(livré)*",
    ("chroma", "lexical"): "chroma + reranking lexical",
    ("local", "cross_encoder"): "local + cross-encoder",
}


def virgule(valeur: float) -> str:
    """0.8636 -> 0,8636. Le livrable est en francais."""
    return f"{valeur:.4f}".replace(".", ",")


def serie(valeurs: list[float]) -> str:
    """Trois valeurs identiques -> `0,8636 x3`. Sinon on les montre toutes."""
    distinctes = set(valeurs)
    if len(distinctes) == 1:
        return f"{virgule(valeurs[0])} ×{len(valeurs)}"
    return "**" + " · ".join(virgule(v) for v in valeurs) + "**"


def mediane_ms(durees: list[int]) -> str:
    ordonnees = sorted(durees)
    valeur = ordonnees[len(ordonnees) // 2]
    return f"{valeur:_} ms".replace("_", " ")


def construire() -> str:
    preuve = json.loads(PREUVE.read_text(encoding="utf-8"))
    essais = preuve["essais_par_configuration"]

    lignes = [
        f"| Configuration | dense R@1, {essais} essais | hybride R@1, {essais} essais "
        f"| Reproductible | Temps médian |",
        "|---|---|---|---|---|",
    ]
    for mesure in preuve["configurations"]:
        cle = (mesure["dense_demande"], mesure["reranker_demande"])
        libelle = LIBELLES.get(cle, f"{cle[0]} + {cle[1]}")
        denses = [e["dense_recall_at_1"] for e in mesure["essais"]]
        hybrides = [e["hybride_recall_at_1"] for e in mesure["essais"]]
        temps = mediane_ms([e["duree_ms"] for e in mesure["essais"]])
        marque = "✅" if mesure["reproductible"] else "❌"
        lignes.append(
            f"| {libelle} | {serie(denses)} | {serie(hybrides)} | {marque} | {temps} |"
        )

    lignes.append("")
    lignes.append(
        "> Généré par `scripts/generer_tableau_briques.py` depuis "
        "`docs/livrable/evidence/comparaison-briques-rag.json`. "
        "**Ne pas modifier a la main** : `--verifier` le signalerait. "
        "La colonne *Reproductible* reprend le champ `reproductible` du fichier de preuve, "
        "calculé sur les valeurs **hybrides**."
    )
    return "\n".join(lignes)


def appliquer(document: Path, tableau: str, verifier: bool) -> str:
    """Renvoie 'absent', 'a jour' ou 'derive'/'ecrit'."""
    if not document.exists():
        return "absent"
    texte = document.read_text(encoding="utf-8")
    if DEBUT not in texte or FIN not in texte:
        return "sans marqueurs"

    avant, reste = texte.split(DEBUT, 1)
    _, apres = reste.split(FIN, 1)
    neuf = f"{avant}{DEBUT}\n{tableau}\n{FIN}{apres}"

    if neuf == texte:
        return "a jour"
    if verifier:
        return "DERIVE"
    document.write_text(neuf, encoding="utf-8")
    return "ecrit"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier", action="store_true",
                        help="signaler une derive sans rien ecrire")
    ns = parser.parse_args()

    tableau = construire()
    problemes = []
    for document in DOCUMENTS:
        etat = appliquer(document, tableau, ns.verifier)
        try:
            nom = document.relative_to(ROOT.parent.parent).as_posix()
        except ValueError:
            nom = document.name
        print(f"  {etat:<14} {nom}")
        if etat in {"DERIVE", "absent", "sans marqueurs"}:
            problemes.append(nom)

    if problemes:
        print(f"\n{len(problemes)} document(s) a corriger. "
              "Relancer sans --verifier." if ns.verifier else
              f"\n{len(problemes)} document(s) en erreur.")
        return 1
    print("\ntableau des briques : les 3 documents disent la preuve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
