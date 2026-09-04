from pydantic import ValidationError
import pytest

from sql.errors import SqlErrorCode, SqlServiceError
from sql.models import (
    QueryResult,
    SemanticColumn,
    SemanticContext,
    SemanticView,
    SqlProposal,
)


def test_sql_proposal_keeps_parameters_separate() -> None:
    proposal = SqlProposal(
        sql=(
            "SELECT statut FROM sorabel_semantic.commandes_support "
            "WHERE id = %(order_id)s"
        ),
        parameters={"order_id": "CMD-2026-0042"},
    )

    assert "CMD-2026-0042" not in proposal.sql
    assert proposal.parameters["order_id"] == "CMD-2026-0042"


def test_empty_sql_proposal_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SqlProposal(sql="   ")


def test_service_error_has_public_code_and_status() -> None:
    error = SqlServiceError(
        SqlErrorCode.OUT_OF_SCHEMA,
        "Donnée absente du schéma visible.",
    )

    assert error.code.value == "OUT_OF_SCHEMA"
    assert error.status == "refused"
    assert str(error) == "Donnée absente du schéma visible."


def test_semantic_context_lists_only_projected_views() -> None:
    context = SemanticContext(
        profile="support",
        dataset_version="dataset-v1",
        data_as_of="2026-09-02",
        semantic_schema_version="semantic-v1",
        policy_version="policy-v1",
        views={
            "commandes_support": SemanticView(
                name="commandes_support",
                description="Commandes visibles par le support.",
                columns={
                    "id": SemanticColumn(
                        name="id",
                        data_type="text",
                        description="Identifiant de commande.",
                    )
                },
            )
        },
    )

    assert context.allowed_views == frozenset({"commandes_support"})
    assert context.allowed_columns("commandes_support") == frozenset({"id"})


def test_query_result_is_json_serializable() -> None:
    result = QueryResult(
        sql="SELECT COUNT(*) AS nombre_commandes FROM commandes_commercial",
        parameters={},
        columns=["nombre_commandes"],
        rows=[[42]],
        backend="postgres",
    )

    payload = result.model_dump(mode="json")
    assert payload["rows"] == [[42]]
    assert payload["row_count"] == 1
