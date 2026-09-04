import json
from pathlib import Path

import pytest

from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode, SqlServiceError
from sql.executors import PostgresExecutor, build_executor
from sql.models import ResolvedQuery
from sql.service import build_sql_service
from sql.settings import SqlBackend, load_sql_settings


CATALOG = SemanticCatalog.load(Path("sql/semantic_catalog.json"))


def _executor(profile: str = "support") -> PostgresExecutor:
    settings = load_sql_settings()
    if settings.effective_backend is not SqlBackend.POSTGRES:
        pytest.skip("PostgreSQL reader DSNs are not configured")
    executor = build_executor(settings, profile)
    assert isinstance(executor, PostgresExecutor)
    return executor


@pytest.mark.postgres
def test_support_executor_reads_authorized_view_in_read_only_transaction() -> None:
    executor = _executor("support")
    try:
        result = executor.execute(
            ResolvedQuery(
                sql=(
                    "SELECT ref, current_setting('transaction_read_only') AS read_only, "
                    "current_setting('statement_timeout') AS statement_timeout "
                    "FROM sorabel_semantic.produits_support ORDER BY ref LIMIT 1"
                ),
                views=("produits_support",),
                columns=("ref",),
                max_rows=100,
            ),
            CATALOG.for_profile("support"),
        )
    finally:
        executor.close()

    assert result.row_count == 1
    assert result.rows[0][1] == "on"
    assert result.rows[0][2] == "3s"
    assert result.backend == "postgres"


@pytest.mark.postgres
def test_database_rejects_write_even_if_validator_is_bypassed() -> None:
    executor = _executor("support")
    try:
        with pytest.raises(SqlServiceError) as captured:
            executor.execute(
                ResolvedQuery(
                    sql="DELETE FROM sorabel_semantic.commandes_support",
                    views=("commandes_support",),
                    columns=(),
                    max_rows=100,
                ),
                CATALOG.for_profile("support"),
            )
    finally:
        executor.close()

    assert captured.value.code is SqlErrorCode.EXECUTION_ERROR


@pytest.mark.postgres
def test_support_database_role_rejects_commercial_margin_view() -> None:
    executor = _executor("support")
    try:
        with pytest.raises(SqlServiceError) as captured:
            executor.execute(
                ResolvedQuery(
                    sql="SELECT marge_ht FROM sorabel_semantic.ventes_commercial LIMIT 1",
                    views=("ventes_commercial",),
                    columns=("marge_ht",),
                    max_rows=100,
                ),
                CATALOG.for_profile("support"),
            )
    finally:
        executor.close()

    assert captured.value.code is SqlErrorCode.EXECUTION_ERROR


def test_developer_profile_has_no_business_data_executor() -> None:
    settings = load_sql_settings()

    with pytest.raises(SqlServiceError) as captured:
        build_executor(settings, "developer")

    assert captured.value.code is SqlErrorCode.NOT_AUTHORIZED


@pytest.mark.postgres
def test_all_business_evaluation_questions_execute_on_postgres() -> None:
    cases = [
        json.loads(line)
        for line in Path("eval/questions_sql.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    service = build_sql_service()
    try:
        for case in cases:
            if case["type"] != "metier":
                continue
            result = service.ask_database(case["question"], case["profil"])
            if case["id"] == "SQL-08":
                assert result.status == "refused"
                assert result.payload["error_code"] == SqlErrorCode.NOT_FOUND.value
                continue
            assert result.status == "ok", f"{case['id']}: {result.message}"
            assert result.payload["backend"] == "postgres"
            assert result.payload["sql"]
    finally:
        service.close()
