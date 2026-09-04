from pathlib import Path

import pytest

from sql.analyzer import AnalysisRoute, QuestionAnalyzer
from sql.catalog import SemanticCatalog
from sql.errors import SqlErrorCode, SqlServiceError


@pytest.fixture
def analyzer() -> QuestionAnalyzer:
    return QuestionAnalyzer()


def _context(profile: str):
    return SemanticCatalog.load(Path("sql/semantic_catalog.json")).for_profile(profile)


@pytest.mark.parametrize(
    ("question", "profile", "code"),
    [
        ("supprime les commandes de test", "commercial", SqlErrorCode.UNSAFE_SQL),
        ("quel est le meilleur client ?", "commercial", SqlErrorCode.AMBIGUOUS_QUESTION),
        ("quelle est la météo à Lille demain ?", "commercial", SqlErrorCode.OUT_OF_SCHEMA),
        ("quelle est la marge sur REF-8842 ?", "support", SqlErrorCode.NOT_AUTHORIZED),
    ],
)
def test_analyzer_refuses_or_clarifies_before_generation(
    analyzer: QuestionAnalyzer, question: str, profile: str, code: SqlErrorCode
) -> None:
    with pytest.raises(SqlServiceError) as captured:
        analyzer.analyze(question, _context(profile))

    assert captured.value.code is code


def test_analyzer_routes_stock_reference_to_fixed_tool(analyzer: QuestionAnalyzer) -> None:
    decision = analyzer.analyze("stock de REF-8842", _context("support"))

    assert decision.route is AnalysisRoute.CHECK_STOCK
    assert decision.parameters == {"ref": "REF-8842"}


def test_analyzer_sends_aggregated_stock_question_to_generator(
    analyzer: QuestionAnalyzer,
) -> None:
    # « stock total » demande une somme : le tool figé renverrait le détail par
    # entrepôt, donc une réponse qui ne répond pas à la question posée.
    decision = analyzer.analyze("quel est le stock total de la REF-8842 ?", _context("support"))

    assert decision.route is AnalysisRoute.ASK_DATABASE


def test_analyzer_routes_order_identifier_to_fixed_tool(analyzer: QuestionAnalyzer) -> None:
    decision = analyzer.analyze("statut de CMD-2026-0042", _context("support"))

    assert decision.route is AnalysisRoute.ORDER_STATUS
    assert decision.parameters == {"order_id": "CMD-2026-0042"}


def test_analyzer_routes_variable_business_analysis_to_generator(
    analyzer: QuestionAnalyzer,
) -> None:
    decision = analyzer.analyze("combien de commandes en avril ?", _context("commercial"))

    assert decision.route is AnalysisRoute.ASK_DATABASE
    assert decision.parameters == {}


#: Formulations d'écriture qui n'emploient pas le vocabulaire exact des listes.
#: Trouvé le 2026-09-04 : « vide le stock de la REF-8842 » renvoyait le stock,
#: en 110 ms, sans le moindre refus. Aucune donnée n'était écrite — check_stock
#: est en lecture seule — mais l'utilisateur repartait en croyant son ordre
#: exécuté. C'est un défaut de communication, pas de sécurité, et il coûte la
#: confiance exactement comme OUT_OF_SCHEMA employé à tort.
ECRITURES_REFORMULEES = [
    "vide le stock de la REF-8842",
    "vide les stocks de LYON",
    "purge la table commandes",
    "purge les commandes annulees",
    "remets a zero le stock de la REF-8842",
    "annule la commande CMD-2025-0005",
    "supprimer les commandes de test",
    "effacer le client CLI-1005",
]


@pytest.mark.parametrize("question", ECRITURES_REFORMULEES)
def test_une_ecriture_reformulee_est_refusee_et_jamais_reinterpretee(question: str) -> None:
    """Une demande d'écriture ne doit jamais devenir une lecture qui répond.

    Le piège que ce test ferme : le routage vers un tool figé regarde la
    référence et le mot « stock », pas le verbe. Sans garde en amont, un ordre
    impératif ressort en rapport de stock.
    """
    analyzer = QuestionAnalyzer()
    with pytest.raises(SqlServiceError) as capture:
        analyzer.analyze(question, _context("support"))
    assert capture.value.code is SqlErrorCode.UNSAFE_SQL, (
        f"« {question} » n'a pas été reconnue comme une écriture"
    )


#: Lectures légitimes qui contiennent un verbe d'écriture — mais pas en position
#: d'ordre. Ce test ferme le défaut inverse : élargir la détection d'écriture ne
#: doit pas refuser des questions parfaitement valides.
LECTURES_LEGITIMES = [
    "combien de produits ont ete ajoutes en avril 2026",
    "quelles commandes ont ete annulees le mois dernier",
    "liste des clients ajoutes cette annee",
    "nombre de commandes annulees par mois",
    "quel est le stock de la REF-8842",
    "combien de commandes en avril 2026",
]


@pytest.mark.parametrize("question", LECTURES_LEGITIMES)
def test_une_lecture_qui_parle_d_ecriture_passee_n_est_pas_refusee(question: str) -> None:
    """« ont été annulées » décrit un fait, « annule » donne un ordre.

    Sans cette distinction, élargir la détection d'écriture reviendrait à
    refuser la moitié des questions métier — un défaut plus visible en
    démonstration que celui qu'on vient de corriger.
    """
    analyzer = QuestionAnalyzer()
    try:
        analyzer.analyze(question, _context("commercial"))
    except SqlServiceError as erreur:
        assert erreur.code is not SqlErrorCode.UNSAFE_SQL, (
            f"« {question} » est une lecture, elle ne doit pas être prise pour une écriture"
        )
