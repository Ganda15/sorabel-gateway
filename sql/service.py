"""Protocol-neutral orchestration for the four governed Sorabel SQL tools."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from sql.analyzer import AnalysisRoute, QuestionAnalyzer
from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode, SqlServiceError
from sql.executors import SqlExecutor, build_executor
from sql.generator import SqlGenerator, build_generator
from sql.models import QueryResult, SemanticContext, SqlProposal, SqlToolResult
from sql.settings import SqlSettings, load_sql_settings
from sql.validator import SqlValidator


ROOT = Path(__file__).resolve().parent.parent
SENSITIVE_SUPPORT_COLUMNS = {"prix_achat_ht", "marge_pct", "marge_ht"}
ExecutorFactory = Callable[[SqlSettings, str], SqlExecutor]


def _error_result(error: SqlServiceError) -> SqlToolResult:
    return SqlToolResult(
        status=error.status,
        payload={"error_code": error.code.value},
        message=error.public_message,
    )


class SqlService:
    def __init__(
        self,
        *,
        catalog: SemanticCatalog,
        settings: SqlSettings,
        analyzer: QuestionAnalyzer | None = None,
        generator: SqlGenerator | None = None,
        validator: SqlValidator | None = None,
        executor_factory: ExecutorFactory = build_executor,
    ) -> None:
        self.catalog = catalog
        self.settings = settings
        self.analyzer = analyzer or QuestionAnalyzer()
        self.generator = generator or build_generator(settings)
        self.validator = validator or SqlValidator()
        self.executor_factory = executor_factory
        self._executors: dict[str, SqlExecutor] = {}

    def _executor(self, profile: str) -> SqlExecutor:
        if profile not in self._executors:
            self._executors[profile] = self.executor_factory(self.settings, profile)
        return self._executors[profile]

    @staticmethod
    def _check_output(result: QueryResult, context: SemanticContext) -> None:
        if context.profile == "support" and SENSITIVE_SUPPORT_COLUMNS.intersection(
            result.columns
        ):
            raise SqlServiceError(
                SqlErrorCode.NOT_AUTHORIZED,
                "Une colonne sensible a été bloquée avant la sortie.",
            )

    def _execute(
        self,
        proposal: SqlProposal,
        context: SemanticContext,
        *,
        not_found_message: str | None = None,
    ) -> SqlToolResult:
        resolved = self.validator.validate(proposal, context, self.settings.max_rows)
        result = self._executor(context.profile).execute(resolved, context)
        self._check_output(result, context)
        if not_found_message is not None and result.row_count == 0:
            raise SqlServiceError(SqlErrorCode.NOT_FOUND, not_found_message)
        return SqlToolResult(status="ok", payload=result.model_dump(mode="json"), message="")

    def get_schema(self, profile: str) -> SqlToolResult:
        try:
            context = self.catalog.for_profile(profile)
            return SqlToolResult(status="ok", payload=context.model_dump(mode="json"), message="")
        except SqlServiceError as error:
            return _error_result(error)

    def check_stock(self, reference: str, profile: str) -> SqlToolResult:
        try:
            normalized_reference = reference.strip().upper()
            if re.fullmatch(r"REF-\d{4}", normalized_reference) is None:
                raise SqlServiceError(
                    SqlErrorCode.INVALID_ARGUMENT,
                    "La référence produit doit respecter le format REF-NNNN.",
                )
            context = self.catalog.for_profile(profile)
            suffix = "support" if profile == "support" else "commercial"
            proposal = SqlProposal(
                sql=(
                    "SELECT ref, entrepot, quantite, seuil_reappro "
                    f"FROM sorabel_semantic.stocks_{suffix} "
                    "WHERE ref = %(reference)s ORDER BY entrepot"
                ),
                parameters={"reference": normalized_reference},
            )
            return self._execute(
                proposal,
                context,
                not_found_message="Aucun stock autorisé ne correspond à cette référence.",
            )
        except SqlServiceError as error:
            return _error_result(error)

    def order_status(self, order_id: str, profile: str) -> SqlToolResult:
        try:
            normalized_order_id = order_id.strip().upper()
            if re.fullmatch(r"CMD-\d{4}-\d{4}", normalized_order_id) is None:
                raise SqlServiceError(
                    SqlErrorCode.INVALID_ARGUMENT,
                    "L’identifiant doit respecter le format CMD-AAAA-NNNN.",
                )
            context = self.catalog.for_profile(profile)
            suffix = "support" if profile == "support" else "commercial"
            proposal = SqlProposal(
                sql=(
                    "SELECT id, date_commande, statut "
                    f"FROM sorabel_semantic.commandes_{suffix} "
                    "WHERE id = %(order_id)s"
                ),
                parameters={"order_id": normalized_order_id},
            )
            return self._execute(
                proposal,
                context,
                not_found_message="Aucune commande autorisée ne correspond à cet identifiant.",
            )
        except SqlServiceError as error:
            return _error_result(error)

    def ask_database(self, question: str, profile: str) -> SqlToolResult:
        try:
            context = self.catalog.for_profile(profile)
            decision = self.analyzer.analyze(question, context)
            if decision.route is AnalysisRoute.CHECK_STOCK:
                return self.check_stock(decision.parameters["ref"], profile)
            if decision.route is AnalysisRoute.ORDER_STATUS:
                return self.order_status(decision.parameters["order_id"], profile)
            proposal = self.generator.generate(question, context)
            return self._execute(proposal, context)
        except SqlServiceError as error:
            return _error_result(error)

    def close(self) -> None:
        for executor in self._executors.values():
            executor.close()
        self._executors.clear()


def build_sql_service(root: Path = ROOT) -> SqlService:
    return SqlService(
        catalog=SemanticCatalog.load(root / "sql" / "semantic_catalog.json"),
        settings=load_sql_settings(),
    )
