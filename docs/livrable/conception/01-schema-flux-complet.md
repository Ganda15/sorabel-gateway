# 1 — Schéma du flux complet

## Architecture logique

```mermaid
flowchart LR
    subgraph Clients[Clients et identité]
      USERS[Support · Commercial · Developer/IDE]
      IDP[Keycloak\ncible d’industrialisation]
      USERS -->|authentification| IDP
      IDP -->|token avec profil| USERS
    end

    subgraph Sources[Sources Sorabel]
      DOCS[Corpus PDF · HTML · Markdown]
      SQLITE[(sorabel.db\n5 tables sources)]
    end

    subgraph RAG[Service RAG avancé]
      ING[Parseurs → catalogue de versions → chunks]
      IDX[Dense + BM25]
      RRF[RRF + reranking]
      EVID[Contrôle de preuve\ncitations ou hors_corpus]
      DOCS --> ING --> IDX --> RRF --> EVID
    end

    subgraph SQL[Service Text-to-SQL]
      IMPORT[Import et réconciliation]
      PG[(PostgreSQL privé)]
      SEM[Vues autorisées + catalogue sémantique versionné]
      GEN[Analyse → génération → AST → allowlists]
      EXEC[Transaction READ ONLY + limites]
      SQLITE --> IMPORT --> PG --> SEM --> GEN --> EXEC
    end

    subgraph MCP[Serveur MCP / Gateway]
      ENTRY[Entrée\ntoken/profil · arguments · request_id]
      AUTH[Matrice profil × tool × collection × SQL]
      CAT[Catalogue de 8 tools\ntools/list]
      VALID[Validation inputSchema\ntools/call]
      ROUTE[Routage RAG ou SQL]
      OUT[Contrat typé + contrôle de sortie]
      AUDIT[(Journal succès et refus)]
      ENTRY --> AUTH
      AUTH --> CAT
      AUTH --> VALID --> ROUTE --> OUT --> AUDIT
    end

    USERS -->|appel MCP direct après login| ENTRY
    CAT -.->|tools visibles| USERS
    ROUTE -->|4 tools RAG| EVID
    ROUTE -->|4 tools SQL| GEN
    EVID --> OUT
    EXEC --> OUT
```

## Lecture

Le corpus documentaire et la base SQL restent deux sources différentes. Le RAG transforme les
documents en chunks recherchables et refuse sans preuve. Le Text-to-SQL importe les cinq tables
dans PostgreSQL, expose des vues sémantiques autorisées et n’exécute que du SQL validé en lecture
seule. Après authentification, le client appelle directement le serveur MCP avec son identité. La
Gateway ne remplace aucun moteur : elle expose les tools, applique la matrice à chaque requête,
valide les arguments, route l’appel, contrôle la réponse et journalise chaque décision.

## Correspondance avec le code

| Bloc | Code principal | Preuve |
|---|---|---|
| ingestion documentaire | `ingest/parsers.py`, `catalog.py`, `chunking.py`, `pipeline.py` | `data/index/manifest.json` |
| retrieval hybride | `retrieval/dense.py`, `lexical.py`, `fusion.py`, `service.py` | `eval/rapport_gain.md` |
| préparation SQL | `scripts/setup_postgres.py`, `sql/migrations/` | preuves PostgreSQL dans `docs/livrable/evidence/` |
| validation et exécution SQL | `sql/analyzer.py`, `generator.py`, `validator.py`, `executors.py`, `service.py` | `eval/rapport_sql.md` |
| gouvernance commune | `application/gateway.py`, `mcp_server/server.py` | `tests/acceptance/test_mcp.py` |
| clients | `scripts/mcp_client.py`, `web_app/` | interface locale et tests d’intégration |

## Point d’honnêteté

Keycloak apparaît comme architecture cible pour produire un token portant le profil. Dans le
prototype vérifié, le profil est encore transmis au processus MCP avec `SORABEL_PROFILE` ;
Keycloak et les tokens multi-clients ne sont donc pas présentés comme déjà implémentés.
