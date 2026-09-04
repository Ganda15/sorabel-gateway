from pathlib import Path

import pytest

from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode, SqlServiceError
from sql.generator import DeterministicSqlGenerator


CONTEXT = SemanticCatalog.load(Path("sql/semantic_catalog.json")).for_profile("commercial")


@pytest.mark.parametrize(
    ("question", "sql_fragments", "parameters"),
    [
        (
            "combien de commandes en avril ?",
            ("COUNT(*)", "commandes_commercial", "date_commande"),
            {"date_debut": "2026-04-01", "date_fin": "2026-05-01"},
        ),
        (
            "quel est le stock total de la REF-8842 ?",
            ("SUM(quantite)", "stocks_commercial"),
            {"reference": "REF-8842"},
        ),
        (
            "liste des commandes livrées en juin 2026",
            ("commandes_commercial", "statut", "date_commande"),
            {"statut": "livree", "date_debut": "2026-06-01", "date_fin": "2026-07-01"},
        ),
        (
            "les 5 produits les plus vendus en quantité",
            ("ventes_commercial", "SUM(v.quantite)", "LIMIT 5"),
            {},
        ),
        (
            "combien de clients à Lille ?",
            ("COUNT(*)", "clients_commercial", "ville"),
            {"ville": "Lille"},
        ),
        (
            "montant total des commandes de mars 2026",
            ("SUM(montant_ht)", "commandes_commercial"),
            {"date_debut": "2026-03-01", "date_fin": "2026-04-01"},
        ),
        (
            "quelles références sont sous leur seuil de réapprovisionnement à LYON ?",
            ("stocks_commercial", "quantite < seuil_reappro", "entrepot"),
            {"entrepot": "LYON"},
        ),
        (
            "statut de la commande CMD-2026-0042",
            ("commandes_commercial", "statut"),
            {"order_id": "CMD-2026-0042"},
        ),
        (
            "combien de commandes annulées depuis janvier 2026 ?",
            ("COUNT(*)", "commandes_commercial", "statut"),
            {"statut": "annulee", "date_debut": "2026-01-01"},
        ),
        (
            "prix de vente HT du disjoncteur tétrapolaire 40 A",
            ("produits_commercial", "prix_vente_ht", "nom"),
            {"nom": "%disjoncteur tétrapolaire 40 A%"},
        ),
        (
            "quelle marge totale sur les ventes de mai 2026 ?",
            ("SUM(v.marge_ht)", "ventes_commercial", "commandes_commercial"),
            {"date_debut": "2026-05-01", "date_fin": "2026-06-01"},
        ),
        (
            "top 3 des clients par montant commandé",
            ("clients_commercial", "commandes_commercial", "LIMIT 3"),
            {},
        ),
    ],
)
def test_deterministic_generator_covers_business_evaluation_questions(
    question: str, sql_fragments: tuple[str, ...], parameters: dict[str, str]
) -> None:
    proposal = DeterministicSqlGenerator().generate(question, CONTEXT)

    assert all(fragment in proposal.sql for fragment in sql_fragments)
    assert proposal.parameters == parameters
    assert "sorabel_semantic." in proposal.sql
    for value in parameters.values():
        assert value not in proposal.sql


def test_generator_uses_support_views_for_support_context() -> None:
    context = SemanticCatalog.load(Path("sql/semantic_catalog.json")).for_profile("support")

    proposal = DeterministicSqlGenerator().generate("combien de clients à Lille ?", context)

    assert "clients_support" in proposal.sql
    assert "commercial" not in proposal.sql


def test_uncovered_phrasing_is_not_reported_as_out_of_schema() -> None:
    # La donnée existe bien dans le schéma : c'est le générateur qui n'a pas de
    # règle pour cette formulation. Annoncer OUT_OF_SCHEMA serait un message faux.
    with pytest.raises(SqlServiceError) as captured:
        DeterministicSqlGenerator().generate(
            "nombre de commandes passees en avril 2026 ?", CONTEXT
        )

    assert captured.value.code is SqlErrorCode.UNSUPPORTED_QUESTION
    assert captured.value.status == "refused"
