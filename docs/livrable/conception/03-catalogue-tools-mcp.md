# 3 — Catalogue des huit tools MCP

## Deux familles, huit contrats

<!-- GENERE:catalogue-tools:debut — ne pas éditer à la main, voir scripts/generer_docs_matrice.py -->
> 🔒 Bloc **généré** depuis `application/access_policy.json`.
> Le modifier ici n'a aucun effet sur le code : modifier la politique, puis relancer
> `uv run python scripts/generer_docs_matrice.py`.

| Famille | Tool | Entrée | Sortie | Garantie | Profils |
|---|---|---|---|---|---|
| RAG | `answer_question` | `question` | réponse rédigée + liste des documents cités | citation obligatoire, sinon hors_corpus | support, commercial |
| RAG | `search_docs` | `query`, `limit` | passages classés avec doc_id, collection, score | recherche sans génération ; collections filtrées en amont | support, commercial, developer |
| RAG | `get_document` | `doc_id`, `version` | texte intégral + métadonnées | document autorisé au profil seulement | support, commercial, developer |
| RAG | `list_sources` | aucune | inventaire des documents du profil | catalogue filtré par profil | support, commercial, developer |
| SQL | `ask_database` | `question` | SQL + paramètres + colonnes + lignes + versions | lecture seule, requête validée, requête rendue vérifiable | support, commercial |
| SQL | `get_schema` | aucune | vues, colonnes, relations, KPI du profil | aucune donnée métier ; schéma physique jamais exposé | commercial, developer |
| SQL | `check_stock` | `reference` | SQL figée + lignes de stock par entrepôt | requête figée et paramétrée | support, commercial |
| SQL | `order_status` | `order_id` | SQL figée + statut de la commande | format vérifié ; requête figée et paramétrée | support, commercial |
<!-- GENERE:catalogue-tools:fin -->

## Comment choisir

```text
Question sur un document ?
  réponse finale avec sources       → answer_question
  passages seulement / inspection   → search_docs
  document précis                   → get_document
  liste des sources visibles        → list_sources

Question sur les données SQL ?
  analyse variable                  → ask_database
  schéma visible                    → get_schema
  stock d’une référence             → check_stock
  statut d’une commande             → order_status
```

Les utilisateurs métier privilégient les tools de haut niveau. Un IDE peut décomposer le travail
avec `search_docs`, `get_document`, `list_sources` et `get_schema` sans demander une réponse finale
ni exécuter une requête de données.

## Gouvernance

L’Agent choisit un tool à partir de sa description. Ce choix ne constitue jamais une autorisation.
`application/gateway.py` et `mcp_server/server.py` vérifient le profil et l’appel. Le service RAG ou
SQL réapplique ensuite son propre périmètre, puis la sortie est contrôlée et auditée.

Toutes les réponses utilisent l’enveloppe :

```json
{"status":"ok|refused|clarification|hors_corpus|execution_error","payload":{},"message":""}
```

Une erreur reste une erreur typée ; le client ne doit jamais l’afficher comme une réponse métier.
