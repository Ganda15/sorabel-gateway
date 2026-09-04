"""Lecture de la politique d'accès — source unique de la matrice.

Avant ce module, les mêmes droits étaient écrits à quatre endroits : deux
dictionnaires Python (`gateway.py`, `retrieval/service.py`) et deux tableaux
Markdown recopiés à la main. Rien ne garantissait qu'ils disent la même chose.

Désormais un seul fichier fait foi — `application/access_policy.json` — et
tout le reste en découle :

* le code lit la politique par ce module ;
* la documentation est régénérée par `scripts/generer_docs_matrice.py` ;
* `tests/unit/test_access_policy.py` échoue si la documentation dérive.

L'axe *colonnes SQL* n'est volontairement pas recopié ici : il est déjà porté
par `sql/semantic_catalog.json`, où chaque vue déclare les profils qui la
voient. La politique le référence au lieu de le dupliquer.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "application" / "access_policy.json"


@lru_cache(maxsize=1)
def load_policy(path: str | None = None) -> dict[str, Any]:
    """Charge la politique et vérifie sa cohérence interne.

    Une politique incohérente doit arrêter le démarrage : une matrice d'accès
    silencieusement fausse est pire qu'une absence de matrice.
    """
    target = Path(path) if path else POLICY_PATH
    policy = json.loads(target.read_text(encoding="utf-8"))
    _validate(policy)
    return policy


def _validate(policy: dict[str, Any]) -> None:
    profils = set(policy["profils"])
    if not profils:
        raise ValueError("La politique ne déclare aucun profil.")

    noms_vus: set[str] = set()
    for tool in policy["tools"]:
        nom = tool["nom"]
        if nom in noms_vus:
            raise ValueError(f"Tool déclaré deux fois dans la politique : {nom}")
        noms_vus.add(nom)
        if not tool["description"].strip():
            raise ValueError(f"Le tool {nom} n'a pas de description.")
        inconnus = set(tool["profils"]) - profils
        if inconnus:
            raise ValueError(f"Le tool {nom} cite des profils inconnus : {sorted(inconnus)}")

    for nom, collection in policy["collections"].items():
        inconnus = set(collection["profils"]) - profils
        if inconnus:
            raise ValueError(
                f"La collection {nom} cite des profils inconnus : {sorted(inconnus)}"
            )


def policy_version(path: str | None = None) -> str:
    return str(load_policy(path)["policy_version"])


def all_tools(path: str | None = None) -> list[str]:
    """Les huit tools du catalogue, dans l'ordre de la politique."""
    return [tool["nom"] for tool in load_policy(path)["tools"]]


def profiles(path: str | None = None) -> list[str]:
    return list(load_policy(path)["profils"])


def tools_by_profile(path: str | None = None) -> dict[str, set[str]]:
    """Axe *tool* de la matrice : quel profil a le droit d'appeler quoi."""
    policy = load_policy(path)
    return {
        profil: {tool["nom"] for tool in policy["tools"] if profil in tool["profils"]}
        for profil in policy["profils"]
    }


def collections_by_profile(path: str | None = None) -> dict[str, set[str]]:
    """Axe *collection documentaire* de la matrice."""
    policy = load_policy(path)
    return {
        profil: {
            nom
            for nom, collection in policy["collections"].items()
            if profil in collection["profils"]
        }
        for profil in policy["profils"]
    }


def tool_specs(profile: str | None = None, path: str | None = None) -> list[dict[str, Any]]:
    """Les contrats des tools, filtrés au profil si un profil est donné."""
    tools = load_policy(path)["tools"]
    if profile is None:
        return list(tools)
    return [tool for tool in tools if profile in tool["profils"]]


def describe(tool: str, path: str | None = None) -> str:
    """La description que l'hôte MCP lit pour choisir ce tool.

    C'est le seul texte dont dispose un agent au moment de choisir : il doit
    dire ce que le tool fait, quand le préférer à un autre, et ce qu'il refuse.
    """
    for spec in load_policy(path)["tools"]:
        if spec["nom"] == tool:
            return str(spec["description"])
    raise KeyError(f"Tool absent de la politique : {tool}")
