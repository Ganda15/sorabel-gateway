# Chantier 2 — Text-to-SQL

## Demande du brief

1. Exposer `get_schema` et `ask_database` sur un schéma métier commenté.
2. Renvoyer la requête SQL avec le résultat.
3. Refuser toute écriture, toute ressource hors périmètre et toute question hors schéma.
4. Protéger les prix d’achat et les marges pour le profil Support.
5. Exposer les tools figés `check_stock` et `order_status`.

## Réalisation

| Besoin | Code principal | Preuve |
|---|---|---|
| Source sémantique versionnée | [`sql/semantic_catalog.json`](../../sql/semantic_catalog.json) | [architecture PostgreSQL](../livrable/architecture/TEXT-TO-SQL-POSTGRESQL-ARCHITECTURE.md) |
| Vues et droits PostgreSQL | [`sql/migrations/`](../../sql/migrations/) | [`postgresql-privileges.json`](../livrable/evidence/postgresql-privileges.json) |
| Décision avant génération | [`sql/analyzer.py`](../../sql/analyzer.py) | [`test_sql_analyzer.py`](../../tests/unit/test_sql_analyzer.py) |
| Génération contrôlée | [`sql/generator.py`](../../sql/generator.py) | [`questions_sql.jsonl`](../../eval/questions_sql.jsonl) |
| Validation AST | [`sql/validator.py`](../../sql/validator.py) | [`test_sql.py`](../../tests/acceptance/test_sql.py) |
| Exécution read-only | [`sql/executors.py`](../../sql/executors.py) | rôles PostgreSQL + transaction `READ ONLY` |
| Quatre tools SQL | [`sql/service.py`](../../sql/service.py) | `ask_database`, `get_schema`, `check_stock`, `order_status` |
| Journal d’audit commun Web + MCP | [`application/audit.py`](../../application/audit.py) | [`test_gateway_journal.py`](../../tests/unit/test_gateway_journal.py) |
| Exactitude métier mesurée | [`scripts/evaluate_sql.py`](../../scripts/evaluate_sql.py) | [`rapport_sql.md`](../../eval/rapport_sql.md) |
| Vue technique d’exécution | [`11-architecture-technique-execution.mmd`](../livrable/architecture/diagrams/11-architecture-technique-execution.mmd) | chemins de fichiers, port, rôles et délais réels |
| Démonstration rejouable | [`GUIDE-DEMONSTRATION.md`](../livrable/GUIDE-DEMONSTRATION.md) | [`demonstration-web.json`](../livrable/evidence/demonstration-web.json) — 26 cas passés par l’interface Web |

## Critères d’acceptance couverts

- « combien de commandes en avril ? » renvoie un résultat correct et le SQL ;
- « supprime les commandes de test » est refusé et journalisé ;
- Support ne reçoit aucune marge ni aucun prix d’achat ;
- une question hors schéma est refusée sans SQL halluciné.

## Résultats mesurés le 2026-09-04

| Mesure | Valeur |
|---|---|
| Suite de tests complète | **168 réussis** (125 unitaires · 12 d’acceptance · 31 d’intégration) |
| Évaluation Text-to-SQL | **27 cas sur 27** |
| Exactitude métier | **14 sur 14**, comparée à une vérité terrain calculée séparément sur `sorabel_source` |
| Générateur SQL actif | **agentique** — `gpt-5.4` via Azure AI Foundry |
| Backend d’exécution | PostgreSQL dédié, un rôle en lecture seule par profil |

L’évaluation mesure deux choses distinctes : la **décision** (accepter, refuser, demander une
précision, et avec quel code) et l’**exactitude** (la valeur renvoyée est-elle la bonne). Une
requête peut être produite, validée, exécutée — et renvoyer un chiffre faux. C’est cette
seconde mesure qui l’attrape.

## Limites assumées

1. **Le générateur actif est agentique.** Un modèle de langage (`gpt-5.4`) reçoit la question
   et le seul schéma autorisé au profil, puis propose le SQL. Il n’a aucune capacité d’appel
   d’outil : la requête envoyée ne contient pas de champ `tools`. Le générateur déterministe
   reste disponible en repli (`SORABEL_SQL_GENERATOR=deterministic`), sans réseau ni latence.
   Le choix du générateur ne change rien à la sécurité — toute proposition traverse les mêmes
   barrières.
2. **Une question hors de portée est refusée**, avec le code `UNSUPPORTED_QUESTION`. Ce code
   est volontairement distinct de `OUT_OF_SCHEMA` : le premier dit que la donnée existe mais
   que la traduction échoue, le second qu’elle n’existe pas. `SQL-27` mesure ce cas — aucune
   date de livraison n’existe en base, et le service refuse plutôt que d’inventer une colonne.
3. **Le passage à l’agentique a un coût** : environ 2 secondes par question au lieu de
   quelques millisecondes, et une dépendance à un fournisseur externe. Les refus de sécurité,
   eux, restent à 0 ms puisqu’ils interviennent avant tout appel au modèle.
4. **Keycloak** n’est pas fait — le filtrage natif de `tools/list` par profil, lui, l’est depuis
   le 2026-09-04. Le profil
   est fourni par l’environnement dans ce prototype.

Le chemin détaillé se trouve dans [04-chemin-text-to-sql.md](../livrable/conception/04-chemin-text-to-sql.md).
