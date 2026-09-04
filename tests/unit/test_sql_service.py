from pathlib import Path

import pytest

from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode
from sql.models import QueryResult, ResolvedQuery, SemanticContext
from sql.service import SqlService
from sql.settings import SqlSettings


class FakeExecutor:
    def __init__(self) -> None:
        self.queries: list[ResolvedQuery] = []

    def execute(self, query: ResolvedQuery, context: SemanticContext) -> QueryResult:
        self.queries.append(query)
        if "COUNT(*)" in query.sql:
            columns, rows = ["nombre_commandes"], [[42]]
        elif "stocks_" in query.sql:
            columns, rows = ["ref", "entrepot", "quantite", "seuil_reappro"], [
                ["REF-8842", "LILLE", 8, 5]
            ]
        elif "commandes_" in query.sql and "WHERE id" in query.sql:
            columns, rows = ["id", "date_commande", "statut"], [
                ["CMD-2026-0042", "2026-04-10", "livree"]
            ]
        else:
            columns, rows = [], []
        return QueryResult(
            sql=query.sql,
            parameters=query.parameters,
            columns=columns,
            rows=rows,
            backend="fake",
            dataset_version=context.dataset_version,
            data_as_of=context.data_as_of,
            semantic_schema_version=context.semantic_schema_version,
            policy_version=context.policy_version,
        )

    def close(self) -> None:
        return None


@pytest.fixture
def service() -> tuple[SqlService, FakeExecutor]:
    executor = FakeExecutor()
    catalog = SemanticCatalog.load(Path("sql/semantic_catalog.json"))
    sql_service = SqlService(
        catalog=catalog,
        settings=SqlSettings(_env_file=None, backend="sqlite"),
        executor_factory=lambda _settings, _profile: executor,
    )
    return sql_service, executor


def test_get_schema_returns_only_profile_filtered_catalogue(
    service: tuple[SqlService, FakeExecutor],
) -> None:
    sql_service, _ = service

    result = sql_service.get_schema("support")

    rendered = str(result.payload)
    assert result.status == "ok"
    assert "produits_support" in rendered
    assert "prix_achat_ht" not in rendered
    assert result.payload["semantic_schema_version"] == "semantic-postgres-v1"


def test_ask_database_returns_rows_sql_parameters_and_versions(
    service: tuple[SqlService, FakeExecutor],
) -> None:
    sql_service, executor = service

    result = sql_service.ask_database("combien de commandes en avril ?", "commercial")

    assert result.status == "ok"
    assert result.payload["rows"] == [[42]]
    assert "SELECT" in result.payload["sql"]
    assert result.payload["parameters"] == {
        "date_debut": "2026-04-01",
        "date_fin": "2026-05-01",
    }
    assert result.payload["policy_version"] == "policy-v1"
    assert executor.queries


@pytest.mark.parametrize(
    ("question", "profile", "code"),
    [
        ("supprime les commandes de test", "commercial", SqlErrorCode.UNSAFE_SQL),
        ("quel est le meilleur client ?", "commercial", SqlErrorCode.AMBIGUOUS_QUESTION),
        ("quelle est la météo demain ?", "commercial", SqlErrorCode.OUT_OF_SCHEMA),
        ("quelle est la marge sur REF-8842 ?", "support", SqlErrorCode.NOT_AUTHORIZED),
    ],
)
def test_ask_database_returns_typed_refusals(
    service: tuple[SqlService, FakeExecutor],
    question: str,
    profile: str,
    code: SqlErrorCode,
) -> None:
    sql_service, _ = service

    result = sql_service.ask_database(question, profile)

    assert result.status in {"refused", "clarification"}
    assert result.payload == {"error_code": code.value}
    assert result.message


def test_fixed_tools_use_parameterized_reviewed_sql(
    service: tuple[SqlService, FakeExecutor],
) -> None:
    sql_service, executor = service

    stock = sql_service.check_stock("ref-8842", "support")
    order = sql_service.order_status("CMD-2026-0042", "support")

    assert stock.status == "ok"
    assert order.status == "ok"
    assert executor.queries[0].parameters == {"reference": "REF-8842"}
    assert "REF-8842" not in executor.queries[0].sql
    assert executor.queries[1].parameters == {"order_id": "CMD-2026-0042"}


@pytest.mark.parametrize(
    ("method", "value"),
    [("check_stock", "bad-reference"), ("order_status", "bad-order")],
)
def test_fixed_tools_reject_invalid_identifiers(
    service: tuple[SqlService, FakeExecutor], method: str, value: str
) -> None:
    sql_service, _ = service

    result = getattr(sql_service, method)(value, "support")

    assert result.status == "refused"
    assert result.payload == {"error_code": SqlErrorCode.INVALID_ARGUMENT.value}
