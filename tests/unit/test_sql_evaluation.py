"""L'évaluation mesure deux choses distinctes : la décision et l'exactitude.

``evaluate_case`` renvoie ``(décision correcte, exactitude correcte, libellé)``.
Un cas n'est réussi que si les deux sont vraies.
"""

from scripts.evaluate_sql import evaluate_case


def test_business_case_requires_sql_and_rows():
    case = {"id": "SQL-01", "type": "metier"}

    decision, _, _ = evaluate_case(
        case, {"status": "ok", "payload": {"sql": "SELECT 1", "rows": [[1]]}}
    )
    assert decision

    decision, _, _ = evaluate_case(case, {"status": "ok", "payload": {"rows": [[1]]}})
    assert not decision


def test_refusal_case_requires_the_expected_typed_error():
    case = {"id": "SQL-13", "type": "ecriture"}

    decision, _, _ = evaluate_case(
        case, {"status": "refused", "payload": {"error_code": "UNSAFE_SQL"}}
    )
    assert decision

    decision, _, _ = evaluate_case(
        case, {"status": "refused", "payload": {"error_code": "OUT_OF_SCHEMA"}}
    )
    assert not decision


def test_business_case_compares_the_value_to_the_ground_truth():
    # Une requête peut être produite, exécutée, et renvoyer la mauvaise valeur.
    # C'est précisément ce que cette vérification attrape.
    case = {"id": "SQL-01", "type": "metier", "attendu_valeur": 27}

    _, exact, _ = evaluate_case(
        case, {"status": "ok", "payload": {"sql": "SELECT 1", "rows": [[27]]}}
    )
    assert exact

    _, exact, libelle = evaluate_case(
        case, {"status": "ok", "payload": {"sql": "SELECT 1", "rows": [[26]]}}
    )
    assert not exact
    assert "26" in libelle


def test_business_case_compares_the_row_count():
    case = {"id": "SQL-04", "type": "metier", "attendu_lignes": 5}

    _, exact, _ = evaluate_case(
        case, {"status": "ok", "payload": {"sql": "SELECT 1", "rows": [], "row_count": 5}}
    )
    assert exact

    _, exact, _ = evaluate_case(
        case, {"status": "ok", "payload": {"sql": "SELECT 1", "rows": [], "row_count": 4}}
    )
    assert not exact


def test_decimal_values_are_compared_numerically():
    # PostgreSQL renvoie un numeric sérialisé en chaîne : « 432245.90 ».
    case = {"id": "SQL-06", "type": "metier", "attendu_valeur": 432245.90}

    _, exact, _ = evaluate_case(
        case, {"status": "ok", "payload": {"sql": "SELECT 1", "rows": [["432245.90"]]}}
    )
    assert exact


def test_uncovered_phrasing_is_a_category_of_its_own():
    # Une formulation non couverte n'est pas une donnée absente du schéma.
    case = {"id": "SQL-25", "type": "non_couverte"}

    decision, _, _ = evaluate_case(
        case, {"status": "refused", "payload": {"error_code": "UNSUPPORTED_QUESTION"}}
    )
    assert decision

    decision, _, _ = evaluate_case(
        case, {"status": "refused", "payload": {"error_code": "OUT_OF_SCHEMA"}}
    )
    assert not decision
