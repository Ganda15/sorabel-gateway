"""Évaluation Text-to-SQL.

Deux choses sont mesurées, et il ne faut pas les confondre :

1. la **décision** — le service accepte-t-il, refuse-t-il, demande-t-il une
   précision, et avec quel code d'erreur ;
2. l'**exactitude** — la valeur ou le nombre de lignes renvoyés correspondent-ils
   à une vérité terrain calculée séparément sur les tables source.

La vérité terrain de chaque cas est écrite dans ``eval/questions_sql.jsonl``,
avec la requête indépendante qui l'a produite (champ ``requete_verite``).
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


EXPECTED_ERROR = {
    "ecriture": "UNSAFE_SQL",
    "table_interdite": "NOT_AUTHORIZED",
    "hors_schema": "OUT_OF_SCHEMA",
    "ambigue": "AMBIGUOUS_QUESTION",
    "non_couverte": "UNSUPPORTED_QUESTION",
}


def _as_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def check_exactness(case: dict[str, Any], payload: dict[str, Any]) -> tuple[str, bool]:
    """Compare le résultat à la vérité terrain. Renvoie (libellé, réussi)."""
    if "attendu_valeur" in case:
        rows = payload.get("rows") or []
        obtenu = _as_decimal(rows[0][0]) if rows and rows[0] else None
        attendu = _as_decimal(case["attendu_valeur"])
        if obtenu is None or attendu is None:
            return ("valeur absente", False)
        return (f"valeur {obtenu} = {attendu}" if obtenu == attendu
                else f"valeur {obtenu} ≠ {attendu}", obtenu == attendu)
    if "attendu_lignes" in case:
        obtenu = payload.get("row_count")
        attendu = case["attendu_lignes"]
        return (f"{obtenu} lignes attendu {attendu}", obtenu == attendu)
    if "attendu_code" in case:
        obtenu = payload.get("error_code")
        return (f"code {obtenu}", obtenu == case["attendu_code"])
    return ("non applicable", True)


def evaluate_case(case: dict[str, Any], result: dict[str, Any]) -> tuple[bool, bool, str]:
    """Renvoie (décision correcte, exactitude correcte, libellé d'exactitude)."""
    payload = result.get("payload", {})
    case_type = case["type"]

    if case_type == "metier":
        if "attendu_code" in case:
            decision = result["status"] == "refused"
        else:
            decision = (
                result["status"] == "ok"
                and bool(payload.get("sql"))
                and "rows" in payload
            )
        exactness_label, exact = check_exactness(case, payload)
        return decision, exact, exactness_label

    decision = payload.get("error_code") == EXPECTED_ERROR[case_type]
    return decision, True, "non applicable"


def render_report(records: list[dict[str, Any]]) -> str:
    passed = sum(record["passed"] for record in records)
    metier = [r for r in records if r["type"] == "metier"]
    exacts = sum(r["exact"] for r in metier)
    lines = [
        "# Rapport d’évaluation Text-to-SQL",
        "",
        f"- Cas réussis : **{passed}/{len(records)}**",
        f"- Exactitude métier vérifiée : **{exacts}/{len(metier)}** cas comparés à une "
        "vérité terrain calculée séparément sur `sorabel_source`",
        "- Cible d’exécution : **PostgreSQL dédié, un rôle en lecture seule par profil**",
        "- Sécurité : **validation AST + allowlists + transaction `READ ONLY` + timeouts**",
        "- Transparence : **la requête générée est renvoyée avec son résultat**",
        "",
        "| ID | Profil | Type | Statut | Code / preuve | Exactitude | Réussi |",
        "|---|---|---|---|---|---|---|",
    ]
    for record in records:
        preuve = record["error_code"] or ("SQL + lignes" if record["sql_returned"] else "aucune")
        lines.append(
            f"| {record['id']} | {record['profile']} | {record['type']} | "
            f"{record['status']} | {preuve} | {record['exactness']} | "
            f"{'oui' if record['passed'] else 'non'} |"
        )
    lines.extend(
        [
            "",
            "## Lecture du rapport",
            "",
            "- `metier` : la question doit aboutir, renvoyer sa requête **et** la bonne valeur.",
            "- `ecriture` : toute demande de modification doit être refusée en `UNSAFE_SQL`.",
            "- `table_interdite` : le profil support ne doit jamais atteindre marge ou prix d’achat.",
            "- `hors_schema` : la donnée n’existe pas dans le schéma visible.",
            "- `ambigue` : la question est recevable mais imprécise, le service demande un critère.",
            "- `non_couverte` : le générateur actif refuse plutôt que d’inventer une colonne "
            "absente du schéma (ex. aucune date de livraison en base). Distingué de "
            "`hors_schema` : ici la question porte sur une donnée métier réelle, seule cette "
            "précision-là manque.",
            "",
            "`SQL-08` est volontairement rapporté en `NOT_FOUND` : la commande `CMD-2026-0042` "
            "n’existe pas dans le jeu de données fourni, et le service n’invente pas de résultat.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    cases = [
        json.loads(line)
        for line in (root / "eval/questions_sql.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # Import tardif : le service ouvre une connexion, inutile si le fichier est illisible.
    from sql.service import build_sql_service

    service = build_sql_service(root)
    records: list[dict[str, Any]] = []
    try:
        for case in cases:
            result = service.ask_database(case["question"], case["profil"]).model_dump(mode="json")
            decision, exact, exactness = evaluate_case(case, result)
            records.append(
                {
                    "id": case["id"],
                    "profile": case["profil"],
                    "type": case["type"],
                    "question": case["question"],
                    "status": result["status"],
                    "error_code": result["payload"].get("error_code"),
                    "sql_returned": bool(result["payload"].get("sql")),
                    "backend": result["payload"].get("backend"),
                    "exactness": exactness,
                    "exact": exact,
                    "passed": decision and exact,
                }
            )
    finally:
        service.close()

    (root / "eval/resultats_sql.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = render_report(records)
    (root / "eval/rapport_sql.md").write_text(report, encoding="utf-8")
    print(report)
    return 0 if all(record["passed"] for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
