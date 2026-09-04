# Rapport de vérification finale

Date de vérification : 2026-09-03 (seconde passe, après corrections).

## Résultats

| Contrôle | Résultat |
|---|---|
| liens Markdown relatifs | tous résolus |
| lecture du brief | 3 chantiers reliés au code, aux tests et aux preuves |
| conception demandée | 5 éléments présents séparément |
| présentation principale | 13 slides, matrice des 8 tools, assets présents, aucune note intégrée |
| périmètre GitHub | uniquement code et éléments officiels du livrable |
| ingestion | 400 fichiers, 391 documents, 9 doublons, 315 familles, 520 chunks, 0 erreur |
| évaluation RAG | Recall@1 0,727 → 0,864, gain **+13,6 points** · `reference_exacte` **1,000** |
| évaluation SQL | 27/27 cas · exactitude métier 14/14 vérifiée sur vérité terrain |
| tests d’acceptance | 12 réussis |
| intégration interface Web | 15 réussis |
| suite complète | 168 réussis (125 unitaires · 12 acceptance · 31 intégration) |
| générateur SQL actif | agentique — `gpt-5.4` via Azure AI Foundry ; déterministe en repli |
| Ruff | tous les contrôles réussis |
| mypy | aucun problème dans 34 fichiers source |
| `git diff --check` | aucune erreur d’espace ou de patch |
| démonstration navigateur | exemples préremplis absents ; sources RAG ; preuves SQL ; détails SQL/paramètres ; refus `UNSAFE_SQL` vérifiés |
| preuve RAG | titre, référence et date affichés depuis la réponse serveur |
| preuve SQL | backend, vue autorisée, colonnes, nombre de lignes, date et versions affichés ; SQL et paramètres dépliables |
| responsive | 375 px portrait et 812 × 375 px paysage sans débordement horizontal, détails SQL ouverts |
| accessibilité | bloc `details` piloté au clavier, focus conservé sur `SUMMARY` |
| console navigateur | aucune erreur |

## Commandes utilisées

Les exécutables de l’environnement déjà installé ont été appelés directement afin de ne pas
dépendre du réseau :

```powershell
.\.venv\Scripts\python.exe scripts\ingest_corpus.py
.\.venv\Scripts\python.exe scripts\evaluate_rag.py
.\.venv\Scripts\python.exe scripts\evaluate_sql.py
.\.venv\Scripts\python.exe -m pytest tests\acceptance -q --basetemp=.pytest-tmp-final-acceptance -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp-final-ui-evidence -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests\integration\test_web_app.py -q -p no:cacheprovider
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe ingest retrieval sql mcp_server application web_app
node --check docs\livrable\presentation\app.js
git diff --check
```

## Avertissements observés

- certains PDF contiennent un pointeur `startxref` incorrect ; `pypdf` récupère leurs object
  streams et le manifeste final ne contient aucune erreur de parsing ;
- la suite complète affiche 14 avertissements de dépendances : un avertissement Starlette/httpx et
  13 avertissements Chroma/Pydantic. Ils ne provoquent aucun échec applicatif ;
- l’accès direct à l’API Docker était interdit dans l’environnement de vérification, mais les tests
  d’intégration PostgreSQL et l’évaluation SQL ont atteint la base configurée et ont réussi.

## Conclusion

Les documents, la présentation, le RAG, Text-to-SQL, MCP, l’interface et les preuves sont cohérents
avec le contrat local du dépôt. Le filtrage de `tools/list` par profil est fait depuis le 2026-09-04.
Les limites restantes — Keycloak,
session et modèles vectoriels/rerankers de production évalués — sont explicitement marquées comme
travail futur.

L’interface de démonstration rend désormais visibles le profil, l’outil sélectionné, le périmètre,
les preuves documentaires ou SQL et le motif d’un refus. Elle ne présente plus de questions
préremplies. Pour RAG, la preuve contient le titre, la référence et la date. Pour SQL, le résumé
indique le backend, la vue autorisée, les colonnes, le nombre de lignes, la date logique et les
versions ; le SQL exact et ses paramètres restent accessibles dans les détails techniques. Le
navigateur n’invente aucun résultat : il affiche exclusivement l’enveloppe typée renvoyée par les
services ou une ressource sémantique extraite du SQL reçu.
