"""La politique d'accès est la source unique — et rien ne doit en dériver.

Ces tests protègent trois choses :

1. les droits n'ont pas changé silencieusement en passant du code écrit à la
   main à la politique déclarative ;
2. chaque tool expose une description exploitable par un agent ;
3. la documentation livrée dit exactement ce que le code applique.

Le point 3 est le plus important : c'est le défaut le plus coûteux du projet —
un document qui décrit un comportement que le code n'a pas.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from application import policy
from application.gateway import TOOLS_BY_PROFILE
from retrieval.service import COLLECTIONS_BY_PROFILE
from scripts.generer_docs_matrice import CIBLES, appliquer


#: Droits tels qu'ils étaient écrits à la main avant l'extraction de la
#: politique. Recopiés ici volontairement : un test qui lirait la même source
#: que le code ne prouverait rien.
DROITS_HISTORIQUES = {
    "support": {
        "answer_question", "search_docs", "get_document", "list_sources",
        "ask_database", "check_stock", "order_status",
    },
    "commercial": {
        "answer_question", "search_docs", "get_document", "list_sources",
        "ask_database", "get_schema", "check_stock", "order_status",
    },
    "developer": {"search_docs", "get_document", "list_sources", "get_schema"},
}

COLLECTIONS_HISTORIQUES = {
    "support": {"fiches_techniques", "notices", "procedures_sav"},
    "commercial": {"fiches_techniques", "notices", "procedures_sav", "notes_internes"},
    "developer": {"fiches_techniques", "notices", "procedures_sav", "notes_internes"},
}


def test_extraire_la_politique_n_a_change_aucun_droit_sur_les_tools() -> None:
    assert policy.tools_by_profile() == DROITS_HISTORIQUES
    assert TOOLS_BY_PROFILE == DROITS_HISTORIQUES


def test_extraire_la_politique_n_a_change_aucun_droit_sur_les_collections() -> None:
    assert policy.collections_by_profile() == COLLECTIONS_HISTORIQUES
    assert COLLECTIONS_BY_PROFILE == COLLECTIONS_HISTORIQUES


def test_le_catalogue_compte_bien_huit_tools() -> None:
    assert len(policy.all_tools()) == 8


def test_le_support_a_sept_tools_et_pas_get_schema() -> None:
    # Test n° 1 attendu par le dossier de conception du chantier 3.
    autorises = policy.tools_by_profile()["support"]
    assert len(autorises) == 7
    assert "get_schema" not in autorises


@pytest.mark.parametrize("tool", policy.all_tools())
def test_chaque_tool_dit_quand_l_utiliser_et_quand_ne_pas_l_utiliser(tool: str) -> None:
    """Un agent ne dispose que de ce texte pour choisir : il doit être discriminant."""
    description = policy.describe(tool)
    assert len(description) > 150, f"{tool} : description trop pauvre pour départager"
    assert "Utiliser" in description, f"{tool} : ne dit pas quand l'utiliser"
    assert "Ne pas utiliser" in description, f"{tool} : ne dit pas quand l'éviter"


def test_une_politique_qui_cite_un_profil_inconnu_est_refusee(tmp_path: Path) -> None:
    corrompue = json.loads(policy.POLICY_PATH.read_text(encoding="utf-8"))
    corrompue["tools"][0]["profils"].append("fantome")
    chemin = tmp_path / "policy.json"
    chemin.write_text(json.dumps(corrompue, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="profils inconnus"):
        policy.load_policy(str(chemin))


def test_une_politique_sans_description_est_refusee(tmp_path: Path) -> None:
    corrompue = json.loads(policy.POLICY_PATH.read_text(encoding="utf-8"))
    corrompue["tools"][0]["description"] = "   "
    chemin = tmp_path / "policy.json"
    chemin.write_text(json.dumps(corrompue, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="pas de description"):
        policy.load_policy(str(chemin))


def test_un_tool_absent_de_la_politique_ne_peut_pas_etre_decrit() -> None:
    with pytest.raises(KeyError):
        policy.describe("drop_database")


@pytest.mark.parametrize("chemin", list(CIBLES), ids=lambda p: p.name)
def test_la_documentation_livree_ne_derive_pas_de_la_politique(chemin: Path) -> None:
    """Si ce test échoue : `uv run python scripts/generer_docs_matrice.py`."""
    assert appliquer(chemin, CIBLES[chemin], ecrire=False), (
        f"{chemin.name} ne dit plus ce que application/access_policy.json applique. "
        "Régénérer avec scripts/generer_docs_matrice.py."
    )


@pytest.mark.parametrize(
    "module",
    [
        "retrieval.service",
        "application.policy",
        "application.gateway",
        "sql.service",
        "mcp_server.server",
        "web_app.server",
    ],
)
def test_chaque_module_est_importable_en_premier(module: str) -> None:
    """Régression du 2026-09-04 : import circulaire introduit par la politique.

    `retrieval.service` importait `application.policy`, mais `application`
    chargeait `gateway`, qui importe `retrieval.service`. La suite passait par
    chance — pytest importait `application` en premier. Un seul point d'entrée
    dans l'autre ordre suffisait à casser le service.
    """
    resultat = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=Path(__file__).resolve().parent.parent.parent,
        capture_output=True,
        text=True,
    )
    assert resultat.returncode == 0, f"{module} n'est pas importable seul :\n{resultat.stderr}"
