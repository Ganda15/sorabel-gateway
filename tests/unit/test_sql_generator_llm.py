"""Le générateur agentique : prompt, parsing, refus — sans aucun appel réseau.

Le client HTTP est injecté, donc ces tests tournent hors ligne et restent verts
même sans clé API configurée.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode, SqlServiceError
from sql.generator import (
    OpenAICompatibleSqlGenerator,
    render_authorized_schema,
)


COMMERCIAL = SemanticCatalog.load(Path("sql/semantic_catalog.json")).for_profile("commercial")
SUPPORT = SemanticCatalog.load(Path("sql/semantic_catalog.json")).for_profile("support")


class FausseReponse:
    """Imite juste ce que le générateur utilise d'une réponse httpx."""

    def __init__(self, contenu: str) -> None:
        self._contenu = contenu

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._contenu}}]}


def generateur(contenu: str, journal: list | None = None) -> OpenAICompatibleSqlGenerator:
    def faux_post(url, **kwargs):
        if journal is not None:
            journal.append(kwargs)
        return FausseReponse(contenu)

    return OpenAICompatibleSqlGenerator(
        base_url="https://exemple.test/v1",
        model="modele-test",
        api_key="cle-test",
        post=faux_post,
    )


# --- le schéma envoyé au modèle -------------------------------------------------


def test_le_schema_rendu_est_compact_et_lisible() -> None:
    rendu = render_authorized_schema(COMMERCIAL)

    assert "VIEW sorabel_semantic.commandes_commercial" in rendu
    assert "montant_ht" in rendu
    # Beaucoup plus court que le dump JSON du contexte complet.
    assert len(rendu) < len(json.dumps(COMMERCIAL.model_dump(mode="json")))


def test_le_schema_du_support_ne_contient_aucune_colonne_sensible() -> None:
    # La barrière la plus importante : le modèle ne peut pas divulguer
    # une colonne qu'il n'a jamais vue.
    rendu = render_authorized_schema(SUPPORT)

    assert "prix_achat_ht" not in rendu
    assert "marge_pct" not in rendu
    assert "marge_ht" not in rendu


def test_le_prompt_contient_les_regles_et_le_schema_du_profil() -> None:
    messages = generateur("{}").build_messages("combien de commandes en avril ?", COMMERCIAL)

    systeme, utilisateur = messages[0]["content"], messages[1]["content"]
    assert "Un seul SELECT" in systeme
    assert "Jamais SELECT *" in systeme
    assert "combien de commandes en avril ?" in utilisateur
    assert "commandes_commercial" in utilisateur


# --- le parsing de la réponse ---------------------------------------------------


def test_une_proposition_valide_est_renvoyee() -> None:
    reponse = json.dumps(
        {
            "sql": "SELECT COUNT(*) AS n FROM sorabel_semantic.commandes_commercial "
            "WHERE date_commande >= %(debut)s",
            "parameters": {"debut": "2026-04-01"},
        }
    )

    proposition = generateur(reponse).generate("combien de commandes ?", COMMERCIAL)

    assert proposition.sql.startswith("SELECT COUNT(*)")
    assert proposition.parameters == {"debut": "2026-04-01"}


def test_le_bloc_de_raisonnement_est_retire_avant_le_parsing() -> None:
    # Les modèles raisonneurs préfixent leur réponse d'un bloc <think>.
    reponse = (
        "<think>L'utilisateur veut un comptage, j'utilise la vue commandes.</think>\n"
        '{"sql": "SELECT COUNT(*) AS n FROM sorabel_semantic.commandes_commercial", '
        '"parameters": {}}'
    )

    proposition = generateur(reponse).generate("combien de commandes ?", COMMERCIAL)

    assert "COUNT(*)" in proposition.sql
    assert "<think>" not in proposition.sql


def test_une_proposition_vide_devient_unsupported_question() -> None:
    # Le modèle déclare ne pas savoir traduire : ce n'est ni une panne,
    # ni une donnée absente du schéma.
    with pytest.raises(SqlServiceError) as capture:
        generateur('{"sql": "", "parameters": {}}').generate("blabla", COMMERCIAL)

    assert capture.value.code is SqlErrorCode.UNSUPPORTED_QUESTION
    assert capture.value.status == "refused"


def test_une_reponse_illisible_est_une_erreur_controlee() -> None:
    with pytest.raises(SqlServiceError) as capture:
        generateur("ceci n'est pas du JSON").generate("combien de commandes ?", COMMERCIAL)

    assert capture.value.code is SqlErrorCode.EXECUTION_ERROR


def test_la_temperature_est_nulle_pour_rester_reproductible() -> None:
    journal: list = []
    generateur('{"sql": "SELECT 1", "parameters": {}}', journal).generate("q", COMMERCIAL)

    assert journal[0]["json"]["temperature"] == 0


# --- les deux dialectes du même protocole ---------------------------------------


def test_dialecte_openai_url_et_entete_bearer() -> None:
    gen = generateur('{"sql": "SELECT 1", "parameters": {}}')

    assert gen.endpoint() == "https://exemple.test/v1/chat/completions"
    assert gen.headers() == {"Authorization": "Bearer cle-test"}


def test_dialecte_azure_deploiement_dans_l_url_et_entete_api_key() -> None:
    # Azure identifie le modèle par le déploiement, dans le chemin, et attend
    # un en-tête `api-key` au lieu de `Authorization: Bearer`.
    gen = OpenAICompatibleSqlGenerator(
        base_url="https://mon-ressource.openai.azure.com",
        model="gpt-5.4-deploiement",
        api_key="cle-azure",
        api_style="azure",
        api_version="2024-10-21",
        post=lambda *a, **k: FausseReponse("{}"),
    )

    assert gen.endpoint() == (
        "https://mon-ressource.openai.azure.com/openai/deployments/"
        "gpt-5.4-deploiement/chat/completions?api-version=2024-10-21"
    )
    assert gen.headers() == {"api-key": "cle-azure"}


def test_azure_est_detecte_depuis_l_url_meme_sans_reglage() -> None:
    gen = OpenAICompatibleSqlGenerator(
        base_url="https://autre.openai.azure.com",
        model="d",
        api_key="k",
        post=lambda *a, **k: FausseReponse("{}"),
    )

    assert gen._is_azure is True


def test_azure_ne_met_pas_le_modele_dans_le_corps() -> None:
    journal: list = []

    def faux_post(url, **kwargs):
        journal.append(kwargs)
        return FausseReponse('{"sql": "SELECT 1", "parameters": {}}')

    OpenAICompatibleSqlGenerator(
        base_url="https://r.openai.azure.com",
        model="mon-deploiement",
        api_key="k",
        post=faux_post,
    ).generate("q", COMMERCIAL)

    assert "model" not in journal[0]["json"]


def test_azure_ai_foundry_en_surface_openai_v1_reste_du_dialecte_openai() -> None:
    # Régression : une URL Azure se terminant par /openai/v1 est la surface
    # compatible OpenAI. La traiter comme Azure doublait le chemin et donnait un 404.
    gen = OpenAICompatibleSqlGenerator(
        base_url="https://une-ressource.services.ai.azure.com/openai/v1",
        model="gpt-5.4",
        api_key="k",
        api_style="auto",
        post=lambda *a, **k: FausseReponse("{}"),
    )

    assert gen._is_azure is False
    assert gen.endpoint() == (
        "https://une-ressource.services.ai.azure.com/openai/v1/chat/completions"
    )
    assert gen.headers() == {"Authorization": "Bearer k"}
