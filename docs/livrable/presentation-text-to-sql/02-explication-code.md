# 2 — Montrer le code important

Ne pas lire les fichiers complets. Ouvrir uniquement les fonctions qui prouvent une décision
d’architecture.

## Ordre VS Code

### 1. Entrée Web

**Fichier :** [`web_app/server.py`](../../../web_app/server.py)

- lignes 20–58 : contrats d’entrée et profils acceptés ;
- lignes 87–116 : quatre routes de l’interface ;
- preuve : le Web est un adaptateur HTTP, pas le serveur MCP.

Phrase : « L’interface valide la forme de la requête puis transmet au Gateway ; elle ne contient
pas la logique RAG ou SQL. »

### 2. Gateway et périmètre SQL

**Fichier :** [`application/gateway.py`](../../../application/gateway.py)

- lignes 31–52 : tools autorisés par profil ;
- lignes 67–80 : autorisation ;
- lignes 82–100 : routage vers le service SQL.

Phrase : « La Gateway vérifie l’accès au tool SQL et transmet le périmètre du profil. Le service ne
fait pas confiance au choix du client. »

### 3. Serveur MCP

**Fichier :** [`mcp_server/server.py`](../../../mcp_server/server.py)

- lignes 52–71 : réautorisation, erreur contrôlée et audit ;
- lignes 88–172 : huit tools ;
- ligne 175 : transport `stdio`.

Phrase : « FastMCP expose les contrats de tools. Dans cette version il communique par stdio, pas
par une route `/mcp`. »

### 4. Catalogue sémantique

**Fichiers :** [`sql/semantic_catalog.json`](../../../sql/semantic_catalog.json) et
[`sql/catalog.py`](../../../sql/catalog.py)

- le JSON décrit les vues, colonnes, relations, KPI et versions ;
- `for_profile()` construit seulement le contexte visible pour le profil.

Phrase : « Le générateur ne reçoit jamais le schéma brut ; il reçoit un contrat métier filtré. »

### 5. Analyse de la question

**Fichier :** [`sql/analyzer.py`](../../../sql/analyzer.py)

- `QuestionAnalyzer.analyze()` détecte l’écriture, les données sensibles, les questions ambiguës,
  les outils figés et le hors-schéma.

Phrase : « Une demande manifestement interdite est arrêtée avant la génération SQL. »

### 6. Génération

**Fichier :** [`sql/generator.py`](../../../sql/generator.py)

- `DeterministicSqlGenerator` est actif pour une démonstration reproductible ;
- `OpenAICompatibleSqlGenerator` est disponible mais optionnel ;
- `build_generator()` choisit selon la configuration.

Phrase : « MCP n’exige pas de LLM. Ici le générateur agentique est actif ; le déterministe pourrait
proposer le SQL, mais il ne pourrait jamais l’autoriser. »

### 7. Validation AST

**Fichier :** [`sql/validator.py`](../../../sql/validator.py)

- `SqlValidator.validate()` parse le SQL avec `sqlglot` ;
- les écritures et expressions interdites sont rejetées ;
- tables, colonnes, fonctions, paramètres et limite sont contrôlés.

Phrase : « Le SQL est traité comme une structure AST, pas comme une chaîne de texte à laquelle on
fait confiance. »

### 8. Exécution PostgreSQL

**Fichier :** [`sql/executors.py`](../../../sql/executors.py)

- `PostgresExecutor` utilise un pool ;
- `SET TRANSACTION READ ONLY` interdit les écritures ;
- `statement_timeout` et `lock_timeout` bornent l’exécution ;
- `build_executor()` sélectionne le compte du profil.

Phrase : « Même après validation applicative, PostgreSQL impose encore ses propres droits. »

### 9. Orchestration et sortie

**Fichier :** [`sql/service.py`](../../../sql/service.py)

- `_execute()` enchaîne validation, exécution et contrôle de sortie ;
- `check_stock()` et `order_status()` construisent du SQL figé paramétré ;
- `ask_database()` route ou lance la génération variable.

Phrase : « Les quatre tools SQL réutilisent le même catalogue, le même validateur, le même
exécuteur et les mêmes erreurs typées. »

### 10. Base et privilèges

**Fichiers :** [`sql/migrations/`](../../../sql/migrations/) et
[`scripts/setup_postgres.py`](../../../scripts/setup_postgres.py)

- migration 001 : schéma source privé ;
- migration 002 : vues métier par profil ;
- migration 003 : rôles et `GRANT SELECT` ;
- script : import idempotent et réconciliation.

Phrase : « Les règles de données sont versionnées dans Git et renforcées dans PostgreSQL. »

### 11. Preuves

**Fichiers :**

- [`tests/acceptance/test_sql.py`](../../../tests/acceptance/test_sql.py) ;
- [`tests/acceptance/test_mcp.py`](../../../tests/acceptance/test_mcp.py) ;
- [`evidence/postgresql-privileges.json`](../evidence/postgresql-privileges.json) ;
- [`eval/rapport_sql.md`](../../../eval/rapport_sql.md).

Phrase : « Je ne demande pas de croire le schéma : les scénarios, privilèges et résultats sont
exécutables ou enregistrés comme preuves. »
