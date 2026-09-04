# Sorabel Data Gateway

Point d'accès unique aux données de **Sorabel**, distributeur B2B de matériel électrique et d'outillage professionnel. La gateway expose, via un **serveur MCP**, le corpus documentaire (fiches techniques, notices, procédures SAV, notes internes) et la base SQL (produits, stocks, commandes, clients, ventes) à tous les outils internes — bot Slack du support, IDE des développeurs, poste des commerciaux — sous une gouvernance commune : matrice d'accès par profil, lecture seule stricte côté SQL, journal de tous les appels.

## Features

- Ingestion de 400 documents PDF/HTML/Markdown avec métadonnées, versions, dédoublonnage et chunks traçables
- Recherche documentaire dense locale + BM25 + fusion RRF, réponses sourcées et refus explicite hors corpus
- Adaptateur Chroma idempotent et embedder multilingue optionnel ; fallback local déterministe pour les tests hors ligne
- Source sémantique PostgreSQL : cinq tables réconciliées, vues métier, catalogue versionné et rôles distincts
- Text-to-SQL protégé par analyse préalable, validation AST, allowlists, limites, timeouts et transaction `READ ONLY`
- Quatre tools SQL sur un service commun : `ask_database`, `get_schema`, `check_stock`, `order_status`
- Serveur MCP stdio exposant les huit tools, avec matrice `support`/`commercial`/`developer` et journalisation versionnée
- Gain réellement mesuré : Recall@1 `0,727` dense → `0,818` hybride (`+9,1 points`)
- Client MCP de test jouable avec les deux profils (`scripts/mcp_client.py`)
- Interface Web unifiée : RAG et Text-to-SQL pour Support/Commercial, recherche et schéma pour Developer/IDE
- Évaluation SQL automatisée : 24 cas métier, écriture, accès sensible, hors schéma et ambiguïté

## Contrat d'intégration

La note de cadrage de la DSI (`docs/cadrage_dsi.md`) fait foi : exigences E1–E6,
matrice d'accès, et **contrat d'intégration** — commande de lancement du serveur
(`python -m mcp_server.server`, profil via `SORABEL_PROFILE`, journal via
`GATEWAY_JOURNAL`), catalogue de tools, enveloppe de réponse JSON
`{status, payload, message}` et format du journal. La suite `tests/acceptance/`
consomme la gateway en boîte noire, exactement comme un client interne :
elle est rouge tant que le serveur et ses tools ne tiennent pas ce contrat.

## Stack

- Python 3.11 (géré avec `uv`)
- Chroma pour l'index vectoriel (`docker compose`, port 8002)
- PostgreSQL 18 dédié sur le port local `55432`, avec rôles et vues autorisées
- SQLite comme source reçue, oracle d’acceptance et compatibilité reproductible en lecture seule
- `sqlglot` pour la validation structurelle de l’AST SQL
- SDK MCP (`mcp`) pour le serveur et le client stdio
- FastAPI + Uvicorn pour l'interface locale et son API
- `pypdf` / `beautifulsoup4` pour l'extraction du corpus, `rank-bm25` pour la piste lexicale
- `sentence-transformers` disponible via l'extra `vector` :

```bash
uv sync                       # cœur + outils de dev
uv sync --extra vector        # + sentence-transformers
```

## Démarrage

```bash
make install      # uv sync
make seed         # génère data/sorabel.db (déterministe, aligné sur le corpus)
make ingest       # normalise et découpe les 400 documents
make evaluate     # mesure dense vs hybride et régénère le rapport E6
make up           # PostgreSQL sur 55432 + Chroma sur 8002
make setup-postgres # migrations, import, réconciliation et contrôles RBAC
make evaluate-sql # exécute les 24 cas Text-to-SQL
make test         # tests unitaires, intégration et acceptance
make serve        # serveur MCP stdio (profil via SORABEL_PROFILE)
make client       # client de test (PROFILE=support|commercial)
make web          # interface RAG + Text-to-SQL sur http://127.0.0.1:8780
```

Interface RAG locale :

```bash
uv run uvicorn web_app.server:app --host 127.0.0.1 --port 8780
```

Ouvrir ensuite `http://127.0.0.1:8780`, ou double-cliquer sur
`START-SORABEL-UI.bat` sous Windows. L’interface fonctionnelle est distincte de la
[présentation formateur](docs/livrable/presentation/index.html).

Exemples côté client :

```bash
uv run python scripts/mcp_client.py --profile support --tool search_docs --args '{"query": "REF-8842"}'
uv run python scripts/mcp_client.py --profile commercial --tool ask_database --args '{"question": "combien de commandes en avril ?"}'
uv run python scripts/sql_cli.py ask "combien de commandes en avril ?" --profile commercial
uv run python scripts/sql_cli.py ask "supprime les commandes de test" --profile commercial
```

## État de l’implémentation

Le starter original est conservé par le tag `before-rag-development`. Le RAG avancé, la Gateway
applicative, l’interface Web unifiée, PostgreSQL, les vues sémantiques, les rôles read-only, les
quatre tools SQL et les contrats d’acceptance sont opérationnels. Le générateur de démonstration est
déterministe ; un adaptateur OpenAI-compatible est disponible mais doit être évalué avant
activation. L’intégration Keycloak reste une étape ultérieure du serveur MCP complet.

- [Règles de développement](AGENTS.md)
- [Changelog](CHANGELOG.md)
- [Lecture du brief par chantier](docs/brief/README.md)
- [Chantier 1 — RAG avancé](docs/brief/01-rag-avance.md)
- [Chantier 2 — Text-to-SQL](docs/brief/02-text-to-sql.md)
- [Chantier 3 — MCP et matrice](docs/brief/03-mcp-matrice-acces.md)
- [Livrable complet — point d’entrée formateur](docs/livrable/README.md)
- [Cinq éléments de conception](docs/livrable/conception/README.md)
- [Traçabilité brief, code, tests et preuves](docs/livrable/TRACEABILITE-BRIEF-CODE-PREUVES.md)
- [Présentation complète RAG + Text-to-SQL + MCP](docs/livrable/presentation/index.html)
- [Architecture Text-to-SQL PostgreSQL](docs/livrable/architecture/TEXT-TO-SQL-POSTGRESQL-ARCHITECTURE.md)
- [Architecture RAG avancé](docs/livrable/architecture/RAG-AVANCE-ARCHITECTURE.md)
- [Rapport de vérification](docs/livrable/VERIFICATION-REPORT.md)

## Layout

```
data/
  corpus/             # ~400 documents : fiches/ notices/ (PDF), sav/ (HTML), notes/ (Markdown)
  sorabel.db          # base SQL (hors git — générée par make seed, schéma dans docs/schema.sql)
docs/
  cadrage_dsi.md      # exigences E1–E6, matrice d'accès, contrat d'intégration
  schema.sql          # schéma commenté de la base (colonnes sensibles signalées)
  brief/              # lecture du contrat par chantier
  livrable/           # conception, présentation, guide MCP, traçabilité et preuves
eval/
  questions_rag.jsonl # questions documentaires : couvertes, hors corpus, par référence exacte
  questions_sql.jsonl # questions métier en langage naturel, dont cas limites
ingest/               # parsing, catalogue, versions, chunks, pipeline et adaptateur Chroma
retrieval/            # dense local, BM25, RRF, reranking, réponse et évaluation
application/          # gateway applicative partagée par les clients
web_app/              # API FastAPI et interface Web fonctionnelle
sql/                  # catalogue, génération, validation AST, exécution et migrations PostgreSQL
mcp_server/           # huit tools MCP, matrice, contrats typés et audit commun
scripts/
  seed.py             # génère et peuple data/sorabel.db
  mcp_client.py       # client MCP de test (profils support / commercial)
tests/acceptance/     # suite d'acceptance boîte noire, adossée aux exigences E1–E6
```
