from pathlib import Path

import pytest

from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode, SqlServiceError


CATALOGUE = Path("sql/semantic_catalog.json")
SENSITIVE_NAMES = {"prix_achat_ht", "marge_pct", "marge_ht"}


def test_support_context_never_contains_sensitive_columns_or_sales_view() -> None:
    context = SemanticCatalog.load(CATALOGUE).for_profile("support")

    rendered = context.model_dump_json()
    assert SENSITIVE_NAMES.isdisjoint(rendered.split('"'))
    assert "ventes_commercial" not in context.views
    assert context.allowed_views == frozenset(
        {
            "produits_support",
            "stocks_support",
            "commandes_support",
            "clients_support",
        }
    )


def test_commercial_context_contains_sales_and_margin_semantics() -> None:
    context = SemanticCatalog.load(CATALOGUE).for_profile("commercial")

    assert "ventes_commercial" in context.views
    assert "marge_ht" in context.allowed_columns("ventes_commercial")
    assert "marge_pct" in context.allowed_columns("produits_commercial")
    assert context.kpis["montant_commandes_ht"]


def test_developer_context_has_schema_but_no_query_examples() -> None:
    context = SemanticCatalog.load(CATALOGUE).for_profile("developer")

    assert context.views
    assert context.examples == ()


def test_catalogue_exposes_traceability_versions() -> None:
    context = SemanticCatalog.load(CATALOGUE).for_profile("commercial")

    assert context.dataset_version == "sorabel-seed-2026-v1"
    assert context.data_as_of == "2026-07-31"
    assert context.semantic_schema_version == "semantic-postgres-v1"
    assert context.policy_version == "policy-v1"


def test_unknown_profile_is_refused_without_catalogue_details() -> None:
    catalogue = SemanticCatalog.load(CATALOGUE)

    with pytest.raises(SqlServiceError) as captured:
        catalogue.for_profile("administrator")

    assert captured.value.code is SqlErrorCode.NOT_AUTHORIZED
    assert "administrator" not in str(captured.value)
