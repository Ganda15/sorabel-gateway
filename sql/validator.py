"""Structural PostgreSQL validation for every generated SQL proposal."""

from __future__ import annotations

import re
from typing import NoReturn

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from sql.errors import SqlErrorCode, SqlServiceError
from sql.models import ResolvedQuery, SemanticContext, SqlProposal


ALLOWED_FUNCTIONS = {
    "AVG",
    "COALESCE",
    "COUNT",
    "DATE_TRUNC",
    "LOWER",
    "MAX",
    "MIN",
    "ROUND",
    "SUM",
    "UPPER",
}


def _unsafe(
    message: str = "La requête proposée ne respecte pas la politique de lecture seule.",
) -> NoReturn:
    raise SqlServiceError(SqlErrorCode.UNSAFE_SQL, message)


def _not_authorized() -> NoReturn:
    raise SqlServiceError(
        SqlErrorCode.NOT_AUTHORIZED,
        "La requête utilise une ressource absente du périmètre autorisé.",
    )


def _forbidden_node_types() -> tuple[type[exp.Expression], ...]:
    names = (
        "Alter",
        "Command",
        "Copy",
        "Create",
        "Delete",
        "Drop",
        "Grant",
        "Insert",
        "Into",
        "Lock",
        "Merge",
        "Revoke",
        "TruncateTable",
        "Update",
        "Use",
    )
    return tuple(getattr(exp, name) for name in names if hasattr(exp, name))


def _select_aliases(tree: exp.Expression) -> set[str]:
    aliases: set[str] = set()
    for select in tree.find_all(exp.Select):
        aliases.update(expression.alias for expression in select.expressions if expression.alias)
    return aliases


def _validate_parameters(tree: exp.Expression, proposal: SqlProposal) -> None:
    placeholders = {
        placeholder.this.name
        if isinstance(placeholder.this, exp.Identifier)
        else str(placeholder.this)
        for placeholder in tree.find_all(exp.Placeholder)
    }
    supplied = set(proposal.parameters)
    if placeholders != supplied:
        raise SqlServiceError(
            SqlErrorCode.INVALID_ARGUMENT,
            "Les paramètres SQL proposés ne correspondent pas au contrat attendu.",
        )


def _is_scalar_aggregate(tree: exp.Expression) -> bool:
    return tree.find(exp.AggFunc) is not None and tree.find(exp.Group) is None


def _bound_limit(tree: exp.Query, max_rows: int) -> None:
    if _is_scalar_aggregate(tree):
        return
    limit = tree.args.get("limit")
    if limit is None:
        tree.limit(max_rows, copy=False)
        return
    expression = limit.expression
    if not isinstance(expression, exp.Literal) or not expression.is_int:
        _unsafe("La limite de lignes doit être une valeur entière contrôlable.")
    if int(expression.this) > max_rows:
        tree.limit(max_rows, copy=False)


def _validate_functions(tree: exp.Expression) -> None:
    for function in tree.find_all(exp.Func):
        rendered = function.sql(dialect="postgres")
        call = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*\(", rendered.upper())
        if call is not None and call.group(1) not in ALLOWED_FUNCTIONS:
            _unsafe("La requête utilise une fonction SQL non autorisée.")


def _validate_stars(tree: exp.Expression) -> None:
    for star in tree.find_all(exp.Star):
        if not isinstance(star.parent, exp.Count):
            _unsafe("SELECT * est interdit ; les colonnes doivent être explicites.")


def _resolve_tables(
    tree: exp.Expression, context: SemanticContext
) -> tuple[tuple[str, ...], dict[str, str], set[str]]:
    cte_names = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    views: set[str] = set()
    aliases: dict[str, str] = {}
    for table in tree.find_all(exp.Table):
        if not table.db and table.name in cte_names:
            continue
        if table.db != "sorabel_semantic" or table.name not in context.allowed_views:
            _not_authorized()
        views.add(table.name)
        aliases[table.name] = table.name
        aliases[table.alias_or_name] = table.name
    if not views:
        _not_authorized()
    return tuple(sorted(views)), aliases, cte_names


def _resolve_columns(
    tree: exp.Expression,
    context: SemanticContext,
    aliases: dict[str, str],
    cte_names: set[str],
) -> tuple[str, ...]:
    allowed_anywhere = {
        column for view in context.views.values() for column in view.columns
    }
    select_aliases = _select_aliases(tree)
    resolved: set[str] = set()
    for column in tree.find_all(exp.Column):
        name = column.name
        qualifier = column.table
        if name in select_aliases and not qualifier:
            continue
        if qualifier in cte_names:
            continue
        if qualifier:
            view_name = aliases.get(qualifier)
            if view_name is None or name not in context.allowed_columns(view_name):
                _not_authorized()
        elif name not in allowed_anywhere:
            _not_authorized()
        resolved.add(name)
    return tuple(sorted(resolved))


class SqlValidator:
    def validate(
        self, proposal: SqlProposal, context: SemanticContext, max_rows: int
    ) -> ResolvedQuery:
        if max_rows <= 0:
            raise ValueError("max_rows must be positive")
        try:
            statements = sqlglot.parse(proposal.sql, read="postgres")
        except ParseError as exc:
            raise SqlServiceError(
                SqlErrorCode.UNSAFE_SQL,
                "La proposition SQL est invalide et n’a pas été exécutée.",
            ) from exc
        if len(statements) != 1:
            _unsafe("Une seule instruction SQL est autorisée.")
        tree = statements[0]
        if tree is None:
            _unsafe("Une seule instruction SQL est autorisée.")
        if not isinstance(tree, exp.Query):
            _unsafe()
        forbidden = _forbidden_node_types()
        if any(isinstance(node, forbidden) for node in tree.walk()):
            _unsafe()

        _validate_stars(tree)
        _validate_functions(tree)
        _validate_parameters(tree, proposal)
        views, aliases, cte_names = _resolve_tables(tree, context)
        columns = _resolve_columns(tree, context, aliases, cte_names)
        _bound_limit(tree, max_rows)

        return ResolvedQuery(
            sql=tree.sql(dialect="postgres"),
            parameters=proposal.parameters,
            views=views,
            columns=columns,
            max_rows=max_rows,
        )
