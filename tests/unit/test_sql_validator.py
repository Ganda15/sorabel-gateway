import json
from pathlib import Path

import pytest

from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode, SqlServiceError
from sql.generator import DeterministicSqlGenerator
from sql.models import SqlProposal
from sql.validator import SqlValidator


CATALOG = SemanticCatalog.load(Path("sql/semantic_catalog.json"))


@pytest.mark.parametrize(
    "statement",
    [
        "DELETE FROM sorabel_semantic.commandes_commercial",
        "UPDATE sorabel_semantic.commandes_commercial SET statut = 'livree'",
        "INSERT INTO sorabel_semantic.commandes_commercial(id) VALUES ('x')",
        "DROP VIEW sorabel_semantic.commandes_commercial",
        "COPY sorabel_semantic.commandes_commercial TO '/tmp/orders.csv'",
        "TRUNCATE TABLE sorabel_semantic.commandes_commercial",
        "SELECT 1; SELECT 2",
        "WITH removed AS (DELETE FROM sorabel_source.commandes RETURNING *) SELECT * FROM removed",
        "SELECT * FROM sorabel_semantic.commandes_commercial",
        "SELECT pg_sleep(10) FROM sorabel_semantic.commandes_commercial",
    ],
)
def test_validator_rejects_unsafe_structures(statement: str) -> None:
    with pytest.raises(SqlServiceError) as captured:
        SqlValidator().validate(
            SqlProposal(sql=statement), CATALOG.for_profile("commercial"), max_rows=100
        )

    assert captured.value.code is SqlErrorCode.UNSAFE_SQL


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT prix_achat_ht FROM sorabel_source.produits",
        "SELECT marge_ht AS revenue FROM sorabel_semantic.ventes_commercial",
        (
            "WITH hidden AS (SELECT marge_ht FROM sorabel_source.ventes) "
            "SELECT COUNT(*) FROM hidden"
        ),
    ],
)
def test_support_scope_cannot_be_bypassed_by_alias_or_cte(statement: str) -> None:
    with pytest.raises(SqlServiceError) as captured:
        SqlValidator().validate(
            SqlProposal(sql=statement), CATALOG.for_profile("support"), max_rows=100
        )

    assert captured.value.code is SqlErrorCode.NOT_AUTHORIZED


def test_count_star_is_allowed_without_a_row_limit() -> None:
    resolved = SqlValidator().validate(
        SqlProposal(
            sql="SELECT COUNT(*) AS total FROM sorabel_semantic.commandes_commercial"
        ),
        CATALOG.for_profile("commercial"),
        max_rows=100,
    )

    assert "COUNT(*)" in resolved.sql
    assert "LIMIT" not in resolved.sql
    assert resolved.views == ("commandes_commercial",)


def test_parameterized_aggregate_keeps_parameters_separate() -> None:
    resolved = SqlValidator().validate(
        SqlProposal(
            sql=(
                "SELECT SUM(montant_ht) AS total "
                "FROM sorabel_semantic.commandes_commercial "
                "WHERE date_commande >= %(date_debut)s"
            ),
            parameters={"date_debut": "2026-01-01"},
        ),
        CATALOG.for_profile("commercial"),
        max_rows=100,
    )

    assert "%(date_debut)s" in resolved.sql
    assert "2026-01-01" not in resolved.sql
    assert resolved.parameters == {"date_debut": "2026-01-01"}


def test_missing_limit_is_added_to_row_query() -> None:
    resolved = SqlValidator().validate(
        SqlProposal(sql="SELECT id FROM sorabel_semantic.commandes_support"),
        CATALOG.for_profile("support"),
        max_rows=100,
    )

    assert resolved.sql.endswith("LIMIT 100")


def test_oversized_limit_is_reduced() -> None:
    resolved = SqlValidator().validate(
        SqlProposal(sql="SELECT id FROM sorabel_semantic.commandes_support LIMIT 1000"),
        CATALOG.for_profile("support"),
        max_rows=100,
    )

    assert resolved.sql.endswith("LIMIT 100")


#: Reformulations de SQL-01, ajoutées comme cas "metier" pour le générateur
#: agentique. Le générateur déterministe n'a délibérément aucune règle pour
#: elles — c'est exactement la limite que le passage à l'agentique corrige.
NON_COUVERTES_PAR_LE_DETERMINISTE = {"SQL-25", "SQL-26"}


def test_all_business_evaluation_proposals_pass_the_same_ast_barrier() -> None:
    cases = [
        json.loads(line)
        for line in Path("eval/questions_sql.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    generator = DeterministicSqlGenerator()
    validator = SqlValidator()

    for case in cases:
        if case["type"] != "metier" or case["id"] in NON_COUVERTES_PAR_LE_DETERMINISTE:
            continue
        context = CATALOG.for_profile(case["profil"])
        proposal = generator.generate(case["question"], context)
        try:
            resolved = validator.validate(proposal, context, max_rows=100)
        except SqlServiceError as error:
            pytest.fail(f"{case['id']} failed AST validation: {proposal.sql} ({error})")
        assert resolved.views
