"""Pre-generation routing and refusal decisions for structured-data questions."""

from __future__ import annotations

import re
import unicodedata
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from sql.errors import SqlErrorCode, SqlServiceError
from sql.models import SemanticContext


class AnalysisRoute(str, Enum):
    CHECK_STOCK = "check_stock"
    ORDER_STATUS = "order_status"
    ASK_DATABASE = "ask_database"


class AnalysisDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    route: AnalysisRoute
    normalized_question: str
    parameters: dict[str, str] = Field(default_factory=dict)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.lower().split())


class QuestionAnalyzer:
    #: Verbes d'ecriture, reconnus comme MOTS ENTIERS et en position d'ordre.
    #:
    #: L'ancienne liste cherchait des sous-chaines figees, dont « vide la table ».
    #: Mesure le 2026-09-04 : « vide le stock de la REF-8842 » y echappait, partait
    #: vers le tool figé `check_stock` — qui regarde la reference et le mot « stock »,
    #: pas le verbe — et repondait le stock en 110 ms. Aucune donnee n'etait ecrite,
    #: mais l'utilisateur repartait en croyant son ordre execute.
    #:
    #: On regarde donc le verbe, entier, dans les trois premiers mots : c'est la
    #: position de l'imperatif et de l'infinitif en francais. Une question de
    #: lecture sur une action passee — « combien de produits ont ete ajoutes en
    #: avril » — place son participe plus loin et n'est pas refusee a tort.
    _write_verbs = frozenset({
        "supprime", "supprimes", "supprimez", "supprimer",
        "efface", "effaces", "effacez", "effacer",
        "purge", "purges", "purgez", "purger",
        "vide", "vides", "videz", "vider",
        "modifie", "modifies", "modifiez", "modifier",
        "insere", "inseres", "inserez", "inserer",
        "ajoute", "ajoutes", "ajoutez", "ajouter",
        "annule", "annules", "annulez", "annuler",
        "remets", "remet", "remettez", "remettre",
        "ecrase", "ecrases", "ecrasez", "ecraser",
        "detruis", "detruit", "detruisez", "detruire",
        "renomme", "renommes", "renommez", "renommer",
    })
    #: Nombre de mots examines : la place du verbe dans un ordre en francais.
    _write_verb_window = 3
    #: Mots-cles SQL d'ecriture, refuses ou qu'ils se trouvent dans la phrase.
    _write_keywords = frozenset({
        "delete", "update", "insert", "drop", "truncate", "alter", "create", "grant",
    })
    #: Tournures a plusieurs mots que le seul verbe ne suffit pas a reconnaitre.
    _write_phrases = (
        "mets a jour",
        "mettre a jour",
        "met a jour",
        "remets a zero",
        "remettre a zero",
    )
    _sensitive_phrases = (
        "marge",
        "prix d'achat",
        "prix achat",
        "cout d'achat",
        "cout achat",
    )
    #: Mots qui signalent une somme demandée plutôt qu'un détail ligne à ligne.
    _aggregation_terms = ("total", "somme", "cumul")
    _business_terms = (
        "client",
        "commande",
        "produit",
        "reference",
        "ref-",
        "stock",
        "entrepot",
        "vente",
        "prix",
        "montant",
        "chiffre d'affaires",
        "marge",
        "remise",
        "reapprovisionnement",
        "fabricant",
        "categorie",
    )

    def _is_write_request(self, normalized: str) -> bool:
        """Vrai si la question donne un ordre d'ecriture plutot qu'elle n'interroge.

        Trois signaux, du plus sur au moins sur : un mot-cle SQL n'importe ou,
        une tournure a plusieurs mots, ou un verbe d'ecriture parmi les premiers
        mots. Le dernier signal est volontairement borne a une fenetre : c'est ce
        qui distingue « supprime les commandes » de « combien de commandes ont
        ete supprimees », qui est une lecture legitime.
        """
        mots = normalized.split()
        if any(mot in self._write_keywords for mot in mots):
            return True
        if any(phrase in normalized for phrase in self._write_phrases):
            return True
        return any(mot in self._write_verbs for mot in mots[: self._write_verb_window])

    def analyze(self, question: str, context: SemanticContext) -> AnalysisDecision:
        normalized = _normalize(question)
        if not normalized:
            raise SqlServiceError(
                SqlErrorCode.INVALID_ARGUMENT,
                "La question ne peut pas être vide.",
            )

        if self._is_write_request(normalized):
            raise SqlServiceError(
                SqlErrorCode.UNSAFE_SQL,
                "Cette demande implique une écriture et a été refusée.",
            )

        for ambiguous_phrase, clarification in context.ambiguities.items():
            if _normalize(ambiguous_phrase) in normalized:
                raise SqlServiceError(SqlErrorCode.AMBIGUOUS_QUESTION, clarification)

        if context.profile == "support" and any(
            phrase in normalized for phrase in self._sensitive_phrases
        ):
            raise SqlServiceError(
                SqlErrorCode.NOT_AUTHORIZED,
                "Cette information n’est pas accessible avec le profil authentifié.",
            )

        # Une question d'agrégation ne doit pas partir vers le tool figé : celui-ci
        # renvoie le détail par entrepôt, pas la somme demandée.
        aggregated = any(word in normalized for word in self._aggregation_terms)

        reference_match = re.search(r"\bREF-\d{4}\b", question, flags=re.IGNORECASE)
        if reference_match and "stock" in normalized and not aggregated:
            return AnalysisDecision(
                route=AnalysisRoute.CHECK_STOCK,
                normalized_question=normalized,
                parameters={"ref": reference_match.group(0).upper()},
            )

        order_match = re.search(r"\bCMD-\d{4}-\d{4}\b", question, flags=re.IGNORECASE)
        if order_match and "statut" in normalized:
            return AnalysisDecision(
                route=AnalysisRoute.ORDER_STATUS,
                normalized_question=normalized,
                parameters={"order_id": order_match.group(0).upper()},
            )

        if not any(term in normalized for term in self._business_terms):
            raise SqlServiceError(
                SqlErrorCode.OUT_OF_SCHEMA,
                "La donnée demandée est absente du schéma métier visible.",
            )

        return AnalysisDecision(
            route=AnalysisRoute.ASK_DATABASE,
            normalized_question=normalized,
        )
