"""Interchangeable SQL proposal generators fed only filtered semantic context."""

from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import date
from typing import Protocol

import httpx

from sql.errors import SqlErrorCode, SqlServiceError
from sql.models import SemanticContext, SqlProposal
from sql.settings import SqlGeneratorMode, SqlSettings


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.lower().split())


MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}


def _period(question: str, *, default_year: int = 2026) -> tuple[str, str]:
    normalized = _normalize(question)
    month = next((number for name, number in MONTHS.items() if name in normalized), None)
    if month is None:
        raise SqlServiceError(
            SqlErrorCode.AMBIGUOUS_QUESTION,
            "Précisez le mois ou la période à analyser.",
        )
    year_match = re.search(r"\b(20\d{2})\b", normalized)
    year = int(year_match.group(1)) if year_match else default_year
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


def _view(context: SemanticContext, business_object: str) -> str:
    suffix = "support" if context.profile == "support" else "commercial"
    view_name = f"{business_object}_{suffix}"
    if view_name not in context.allowed_views:
        raise SqlServiceError(
            SqlErrorCode.NOT_AUTHORIZED,
            "Cette information n’est pas accessible avec le profil authentifié.",
        )
    return f"sorabel_semantic.{view_name}"


class SqlGenerator(Protocol):
    def generate(self, question: str, context: SemanticContext) -> SqlProposal: ...


class DeterministicSqlGenerator:
    """Reproducible intent handlers for the supplied Sorabel business evaluation."""

    def generate(self, question: str, context: SemanticContext) -> SqlProposal:
        normalized = _normalize(question)

        if "marge totale" in normalized:
            start, end = _period(question)
            ventes = _view(context, "ventes")
            commandes = _view(context, "commandes")
            return SqlProposal(
                sql=(
                    "SELECT COALESCE(SUM(v.marge_ht), 0) AS marge_totale_ht "
                    f"FROM {ventes} AS v "
                    f"JOIN {commandes} AS c ON c.id = v.commande_id "
                    "WHERE c.date_commande >= %(date_debut)s "
                    "AND c.date_commande < %(date_fin)s"
                ),
                parameters={"date_debut": start, "date_fin": end},
            )

        if "top 3" in normalized and "clients" in normalized:
            clients = _view(context, "clients")
            commandes = _view(context, "commandes")
            return SqlProposal(
                sql=(
                    "SELECT c.id, c.raison_sociale, SUM(o.montant_ht) AS montant_commande_ht "
                    f"FROM {clients} AS c "
                    f"JOIN {commandes} AS o ON o.client_id = c.id "
                    "GROUP BY c.id, c.raison_sociale "
                    "ORDER BY montant_commande_ht DESC LIMIT 3"
                )
            )

        if "produits les plus vendus" in normalized:
            ventes = _view(context, "ventes")
            produits = _view(context, "produits")
            return SqlProposal(
                sql=(
                    "SELECT p.ref, p.nom, SUM(v.quantite) AS quantite_vendue "
                    f"FROM {ventes} AS v "
                    f"JOIN {produits} AS p ON p.ref = v.ref "
                    "GROUP BY p.ref, p.nom ORDER BY quantite_vendue DESC LIMIT 5"
                )
            )

        if "seuil de reapprovisionnement" in normalized:
            warehouse_match = re.search(r"\bà\s+([A-Za-zÀ-ÿ-]+)\s*\??$", question)
            warehouse = warehouse_match.group(1).upper() if warehouse_match else ""
            if not warehouse:
                raise SqlServiceError(
                    SqlErrorCode.AMBIGUOUS_QUESTION,
                    "Précisez l’entrepôt concerné.",
                )
            stocks = _view(context, "stocks")
            return SqlProposal(
                sql=(
                    "SELECT ref, quantite, seuil_reappro "
                    f"FROM {stocks} WHERE entrepot = %(entrepot)s "
                    "AND quantite < seuil_reappro ORDER BY ref"
                ),
                parameters={"entrepot": warehouse},
            )

        if "statut" in normalized and "cmd-" in normalized:
            order_match = re.search(r"\bCMD-\d{4}-\d{4}\b", question, re.IGNORECASE)
            if order_match is None:
                raise SqlServiceError(SqlErrorCode.INVALID_ARGUMENT, "Identifiant de commande invalide.")
            commandes = _view(context, "commandes")
            return SqlProposal(
                sql=f"SELECT id, statut FROM {commandes} WHERE id = %(order_id)s",
                parameters={"order_id": order_match.group(0).upper()},
            )

        if "commandes annulees" in normalized:
            start, _ = _period(question)
            commandes = _view(context, "commandes")
            return SqlProposal(
                sql=(
                    f"SELECT COUNT(*) AS nombre_commandes FROM {commandes} "
                    "WHERE statut = %(statut)s AND date_commande >= %(date_debut)s"
                ),
                parameters={"statut": "annulee", "date_debut": start},
            )

        if "prix de vente" in normalized:
            product_match = re.search(r"\bdu\s+(.+?)\s*\??$", question, re.IGNORECASE)
            product_name = product_match.group(1).strip() if product_match else ""
            if not product_name:
                raise SqlServiceError(
                    SqlErrorCode.AMBIGUOUS_QUESTION,
                    "Précisez le produit recherché.",
                )
            produits = _view(context, "produits")
            return SqlProposal(
                sql=(
                    f"SELECT ref, nom, prix_vente_ht FROM {produits} "
                    "WHERE nom ILIKE %(nom)s ORDER BY nom"
                ),
                parameters={"nom": f"%{product_name}%"},
            )

        if "stock total" in normalized and "ref-" in normalized:
            reference_match = re.search(r"\bREF-\d{4}\b", question, re.IGNORECASE)
            if reference_match is None:
                raise SqlServiceError(SqlErrorCode.INVALID_ARGUMENT, "Référence produit invalide.")
            stocks = _view(context, "stocks")
            return SqlProposal(
                sql=f"SELECT COALESCE(SUM(quantite), 0) AS stock_total FROM {stocks} WHERE ref = %(reference)s",
                parameters={"reference": reference_match.group(0).upper()},
            )

        if "combien de clients" in normalized:
            city_match = re.search(r"\bà\s+([A-Za-zÀ-ÿ-]+)\s*\??$", question)
            city = city_match.group(1) if city_match else ""
            if not city:
                raise SqlServiceError(SqlErrorCode.AMBIGUOUS_QUESTION, "Précisez la ville.")
            clients = _view(context, "clients")
            return SqlProposal(
                sql=f"SELECT COUNT(*) AS nombre_clients FROM {clients} WHERE ville = %(ville)s",
                parameters={"ville": city},
            )

        if "montant total" in normalized and "commandes" in normalized:
            start, end = _period(question)
            commandes = _view(context, "commandes")
            return SqlProposal(
                sql=(
                    f"SELECT COALESCE(SUM(montant_ht), 0) AS montant_total_ht FROM {commandes} "
                    "WHERE date_commande >= %(date_debut)s AND date_commande < %(date_fin)s"
                ),
                parameters={"date_debut": start, "date_fin": end},
            )

        if "liste des commandes livrees" in normalized:
            start, end = _period(question)
            commandes = _view(context, "commandes")
            return SqlProposal(
                sql=(
                    f"SELECT id, client_id, date_commande, statut, montant_ht FROM {commandes} "
                    "WHERE statut = %(statut)s AND date_commande >= %(date_debut)s "
                    "AND date_commande < %(date_fin)s ORDER BY date_commande, id"
                ),
                parameters={"statut": "livree", "date_debut": start, "date_fin": end},
            )

        if "combien de commandes" in normalized:
            start, end = _period(question)
            commandes = _view(context, "commandes")
            return SqlProposal(
                sql=(
                    f"SELECT COUNT(*) AS nombre_commandes FROM {commandes} "
                    "WHERE date_commande >= %(date_debut)s AND date_commande < %(date_fin)s"
                ),
                parameters={"date_debut": start, "date_fin": end},
            )

        # La donnée demandée peut très bien exister dans le schéma : c'est ce
        # générateur qui n'a pas de règle pour cette formulation. Le distinguer
        # de OUT_OF_SCHEMA évite d'annoncer une absence de donnée qui est fausse.
        raise SqlServiceError(
            SqlErrorCode.UNSUPPORTED_QUESTION,
            "Cette formulation n’est pas encore couverte par une requête validée. "
            "Reformulez la question ou utilisez un tool dédié.",
        )


#: Le modèle ne reçoit jamais le schéma brut : il reçoit ce rendu, construit
#: à partir du seul catalogue déjà filtré par profil.
def render_authorized_schema(context: SemanticContext) -> str:
    """Rend le périmètre autorisé en DDL commenté, compact et lisible par un modèle."""
    lignes: list[str] = []
    for view in context.views.values():
        colonnes = ", ".join(f"{c.name} {c.data_type}" for c in view.columns.values())
        lignes.append(f"-- {view.description}")
        lignes.append(f"VIEW sorabel_semantic.{view.name} ({colonnes})")
    if context.relations:
        lignes.append("-- jointures vérifiées :")
        for relation in context.relations:
            lignes.append(f"--   {relation}")
    if context.kpis:
        lignes.append("-- indicateurs métier approuvés :")
        for nom, definition in context.kpis.items():
            lignes.append(f"--   {nom} = {definition}")
    return "\n".join(lignes)


SQL_SYSTEM_PROMPT = """Tu traduis une question métier française en UNE requête SQL PostgreSQL de lecture.

RÈGLES ABSOLUES
- Un seul SELECT. Jamais INSERT, UPDATE, DELETE, DROP, CREATE, GRANT, TRUNCATE.
- Jamais de sous-requête (pas de FROM (SELECT ...)). Pour compter des valeurs distinctes,
  utilise COUNT(DISTINCT colonne) directement dans le SELECT principal.
- Utilise UNIQUEMENT les vues et colonnes du schéma fourni. Rien d'autre n'existe.
- Jamais SELECT *. Nomme toujours les colonnes.
- Toute valeur littérale passe par un paramètre nommé psycopg : %(nom)s
- EXCEPTION : le nombre après LIMIT s'écrit en clair, jamais en paramètre. LIMIT 3, pas LIMIT %(limit)s.
- Fonctions autorisées uniquement : AVG, COALESCE, COUNT, DATE_TRUNC, LOWER, MAX, MIN, ROUND, SUM, UPPER
- Si la question ne peut pas être traduite avec ce schéma, renvoie une chaîne sql vide.

CONVENTIONS DES DONNÉES — les ignorer donne un résultat vide
- Les CODES DE STATUT sont sans accent et en minuscules : 'livree', 'annulee', 'en_cours'.
  Jamais 'livrée'. Cette règle ne vaut QUE pour les statuts.
- Les LIBELLÉS (noms de produits, raisons sociales, villes) gardent leurs accents tels quels :
  écris bien 'tétrapolaire', pas 'tetrapolaire'.
- Un libellé se cherche toujours par correspondance partielle, jamais par égalité :
  `nom ILIKE %(nom)s` avec un paramètre encadré de %, par exemple '%disjoncteur tétrapolaire 40 A%'.
- Une période « en avril 2026 » se borne par deux dates : >= '2026-04-01' ET < '2026-05-01'.

Réponds UNIQUEMENT en JSON, sans texte autour :
{"sql": "...", "parameters": {...}}"""


def _strip_reasoning(content: str) -> str:
    """Retire les blocs <think> des modèles raisonneurs avant le parsing JSON."""
    return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()


class OpenAICompatibleSqlGenerator:
    """Générateur agentique : le modèle propose, il n'autorise jamais.

    La proposition produite ici traverse ensuite exactement les mêmes barrières
    que celle du générateur déterministe — analyseur, validateur AST, rôle
    PostgreSQL en lecture seule.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        api_style: str = "auto",
        api_version: str = "2024-10-21",
        post=None,
        sleep=None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        #: "auto" (déduit de l'URL), "openai" ou "azure" — deux dialectes du même protocole.
        self.api_style = api_style
        self.api_version = api_version
        #: Injectables pour les tests : évitent tout appel réseau et toute attente.
        self._post = post or httpx.post
        self._sleep = sleep or time.sleep

    @property
    def _is_azure(self) -> bool:
        """Vrai seulement pour la surface Azure « deployments », pas pour /openai/v1.

        Azure AI Foundry expose aussi un endpoint compatible OpenAI standard, qui se
        termine par /openai/v1 : celui-là se parle comme OpenAI, sans déploiement
        dans le chemin.
        """
        if self.api_style == "azure":
            return True
        if self.api_style != "auto":
            return False
        return ".azure.com" in self.base_url and "/openai/v1" not in self.base_url

    def endpoint(self) -> str:
        """URL d'appel. Azure place le déploiement dans le chemin, pas dans le corps."""
        if self._is_azure:
            return (
                f"{self.base_url}/openai/deployments/{self.model}"
                f"/chat/completions?api-version={self.api_version}"
            )
        return f"{self.base_url}/chat/completions"

    def headers(self) -> dict[str, str]:
        """Azure attend `api-key`, les autres `Authorization: Bearer`."""
        if self._is_azure:
            return {"api-key": self.api_key}
        return {"Authorization": f"Bearer {self.api_key}"}

    def build_messages(self, question: str, context: SemanticContext) -> list[dict[str, str]]:
        """Construit les deux messages envoyés au modèle. Testable sans réseau."""
        utilisateur = (
            f"SCHÉMA AUTORISÉ (profil {context.profile}, données au {context.data_as_of}) :\n"
            f"{render_authorized_schema(context)}\n\n"
            f"QUESTION : {question}"
        )
        return [
            {"role": "system", "content": SQL_SYSTEM_PROMPT},
            {"role": "user", "content": utilisateur},
        ]

    def _appeler(self, question: str, context: SemanticContext):
        """Appelle le modèle, en réessayant si le fournisseur limite le débit.

        Les offres gratuites plafonnent les tokens par minute : un 429 n'est pas
        une panne, c'est une attente. On réessaie, puis on abandonne proprement.
        """
        corps: dict[str, object] = {
            "messages": self.build_messages(question, context),
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        if not self._is_azure:
            # Azure identifie le modèle par le déploiement, présent dans l'URL.
            corps["model"] = self.model
        derniere = None
        for tentative in range(self.max_retries + 1):
            reponse = self._post(
                self.endpoint(),
                headers=self.headers(),
                json=corps,
                timeout=self.timeout,
            )
            if getattr(reponse, "status_code", 200) != 429:
                return reponse
            derniere = reponse
            if tentative < self.max_retries:
                attente = float(reponse.headers.get("retry-after", 0) or 0)
                self._sleep(min(max(attente, 2.0 * (tentative + 1)), 30.0))
        return derniere

    def generate(self, question: str, context: SemanticContext) -> SqlProposal:
        try:
            response = self._appeler(question, context)
            response.raise_for_status()
            contenu = _strip_reasoning(response.json()["choices"][0]["message"]["content"])
            propose = json.loads(contenu)
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise SqlServiceError(
                SqlErrorCode.EXECUTION_ERROR,
                "Le générateur SQL configuré n’a pas produit de proposition exploitable.",
            ) from exc

        sql = str(propose.get("sql") or "").strip()
        if not sql:
            # Le modèle a explicitement déclaré ne pas pouvoir traduire la question.
            raise SqlServiceError(
                SqlErrorCode.UNSUPPORTED_QUESTION,
                "Cette question n’a pas pu être traduite dans le périmètre autorisé.",
            )
        return SqlProposal(sql=sql, parameters=propose.get("parameters") or {})


def build_generator(settings: SqlSettings) -> SqlGenerator:
    if settings.generator is SqlGeneratorMode.DETERMINISTIC:
        return DeterministicSqlGenerator()
    if not settings.llm_base_url or not settings.llm_model or settings.llm_api_key is None:
        raise SqlServiceError(
            SqlErrorCode.EXECUTION_ERROR,
            "La configuration du générateur SQL distant est incomplète.",
        )
    return OpenAICompatibleSqlGenerator(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key.get_secret_value(),
        timeout=settings.llm_timeout_seconds,
        api_style=settings.llm_api_style,
        api_version=settings.llm_api_version,
    )
