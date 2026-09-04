"""Vérifie que chaque référence `fichier.py:ligne` citée dans la documentation
pointe bien sur ce qu'elle prétend.

Le défaut qu'il attrape : modifier un fichier source décale ses lignes, et
toutes les références écrites dans les documents deviennent fausses en silence.
Un numéro faux projeté devant un jury invite à ouvrir le fichier et à ne rien
trouver — c'est pire que pas de numéro du tout.

Méthode : pour chaque `chemin.py:N` trouvé, on lit la ligne N et on cherche,
dans les 200 caractères qui entourent la référence dans le document, un symbole
entre accents graves (`ma_fonction`) ou en gras. Si le document nomme un symbole
et que la ligne visée ne le contient pas, c'est signalé.

    uv run python scripts/verifier_references_code.py
    uv run python scripts/verifier_references_code.py --racine ..
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# La console Windows est en cp1252 : forcer l'UTF-8 sur la sortie evite un
# UnicodeEncodeError sur les noms de fichiers accentues.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parent.parent

#: `application/gateway.py:42` ou application/gateway.py#L42
REFERENCE = re.compile(r"([\w./-]+\.py)[:#]L?(\d+)")
#: Un symbole cité entre accents graves : `_authorize`, `TOOLS_BY_PROFILE`
#: On exige un underscore ou une majuscule : un mot français entre accents
#: graves n'est pas un symbole de code.
SYMBOLE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*[_A-Z][A-Za-z0-9_]*)`")

IGNORER = {".venv", "node_modules", ".git", "__pycache__", ".test-tmp", ".uv-cache",
           ".mypy_cache", ".pytest_cache", ".ruff_cache", ".docker-data"}


def ligne_du_document(texte: str, position: int) -> str:
    """La ligne Markdown qui porte la référence — souvent une ligne de tableau.

    Regarder plus large produit des faux positifs : le document cite un symbole
    deux lignes plus haut et on l'attribue à tort à cette référence.
    """
    debut = texte.rfind("\n", 0, position) + 1
    fin = texte.find("\n", position)
    return texte[debut : fin if fin != -1 else len(texte)]


def verifier(racine: Path, base_code: Path) -> tuple[int, list[str]]:
    total = 0
    problemes: list[str] = []

    for document in sorted(racine.rglob("*.md")) + sorted(racine.rglob("*.mmd")):
        if any(part in IGNORER for part in document.parts):
            continue
        texte = document.read_text(encoding="utf-8", errors="replace")

        for trouve in REFERENCE.finditer(texte):
            chemin_cite, numero = trouve.group(1), int(trouve.group(2))
            cible = base_code / chemin_cite
            if not cible.exists():
                # Beaucoup de documents citent des chemins relatifs à leur
                # propre dossier ; on ne signale que ce qu'on sait résoudre.
                continue
            total += 1

            lignes = cible.read_text(encoding="utf-8", errors="replace").split("\n")
            if numero < 1 or numero > len(lignes):
                problemes.append(
                    f"{document.relative_to(racine).as_posix()} → {chemin_cite}:{numero} "
                    f"— le fichier n'a que {len(lignes)} lignes"
                )
                continue

            ligne = lignes[numero - 1]
            autour = ligne_du_document(texte, trouve.start())
            symboles = {s for s in SYMBOLE.findall(autour) if not s.endswith(".py")}
            # On ne juge que si le document nomme un symbole plausible.
            candidats = [s for s in symboles if s in ligne]
            if symboles and not candidats and ligne.strip():
                problemes.append(
                    f"{document.relative_to(racine).as_posix()} → {chemin_cite}:{numero}\n"
                    f"      document : {', '.join(sorted(symboles)[:4])}\n"
                    f"      ligne    : {ligne.strip()[:70]}"
                )
            elif not ligne.strip():
                problemes.append(
                    f"{document.relative_to(racine).as_posix()} → {chemin_cite}:{numero} "
                    f"— pointe sur une ligne vide"
                )

    return total, problemes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--racine", default=".", help="où chercher les documents")
    parser.add_argument("--code", default=".", help="racine du code source")
    ns = parser.parse_args()

    racine = Path(ns.racine).resolve()
    base_code = Path(ns.code).resolve()
    total, problemes = verifier(racine, base_code)

    print(f"{total} références vérifiées dans {racine.name}")
    if not problemes:
        print("Aucune référence suspecte.")
        return 0

    print(f"\n{len(problemes)} référence(s) à contrôler :\n")
    for probleme in problemes:
        print(f"  [!] {probleme}")
    print(
        "\nUne référence signalée n'est pas forcément fausse : le document peut nommer "
        "un symbole voisin. Vérifier à la main."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
