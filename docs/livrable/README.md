# Livrable formateur — Sorabel Data Gateway

Ce dossier rassemble uniquement les éléments officiels à remettre ou à présenter. Il couvre les
trois chantiers du brief : RAG avancé, Text-to-SQL, puis serveur MCP et matrice d’accès.

## Parcours recommandé

1. [Brief local par chantier](../brief/README.md)
2. [Dossier des cinq éléments de conception](conception/README.md)
3. [Traçabilité brief → code → tests → preuves](TRACEABILITE-BRIEF-CODE-PREUVES.md)
4. [Mini-guide d’accès au serveur MCP](GUIDE-ACCES-MCP.md)
5. [Présentation finale](presentation/index.html)
6. [Preuves versionnées](evidence/)
7. [Rapport de vérification](VERIFICATION-REPORT.md)

Sous Windows, `OPEN-VSCODE-PRESENTATION.bat` ouvre les principaux fichiers de démonstration dans
VS Code. `presentation/START-PRESENTATION.bat` ouvre le support visuel.

## Les cinq éléments demandés

| Élément | Document |
|---|---|
| Schéma de flux complet | [01-schema-flux-complet.md](conception/01-schema-flux-complet.md) |
| Modèle des chunks et métadonnées | [02-modele-chunks-metadonnees.md](conception/02-modele-chunks-metadonnees.md) |
| Catalogue des huit tools MCP | [03-catalogue-tools-mcp.md](conception/03-catalogue-tools-mcp.md) |
| Chemin Text-to-SQL | [04-chemin-text-to-sql.md](conception/04-chemin-text-to-sql.md) |
| Matrice profil × tool × ressource | [05-matrice-acces.md](conception/05-matrice-acces.md) |

## Code correspondant aux trois chantiers

| Chantier | Responsabilités | Répertoires principaux |
|---|---|---|
| RAG avancé | parsing, versions, chunks, dense, BM25, RRF, preuve et citations | `ingest/`, `retrieval/` |
| Text-to-SQL | catalogue sémantique, génération, AST, allowlists et exécution read-only | `sql/` |
| MCP et matrice | huit contrats, autorisation, routage, erreurs typées et audit | `application/`, `mcp_server/` |
| Démonstration | CLI et interface Web utilisant les mêmes services | `scripts/`, `web_app/` |

Les architectures détaillées sont disponibles dans :

- [architecture complète réellement démontrée](architecture/ARCHITECTURE-COMPLETE-SORABEL.md) ;
- [RAG-AVANCE-ARCHITECTURE.md](architecture/RAG-AVANCE-ARCHITECTURE.md) ;
- [TEXT-TO-SQL-POSTGRESQL-ARCHITECTURE.md](architecture/TEXT-TO-SQL-POSTGRESQL-ARCHITECTURE.md) ;
- les sources Mermaid zoomables dans [`architecture/diagrams/`](architecture/diagrams/).

Le parcours de présentation **schéma → code → démonstration** est disponible dans
[`presentation-text-to-sql/`](presentation-text-to-sql/README.md).

## Démonstration reproductible

> 📘 **Le déroulé complet de la démonstration Text-to-SQL, avec les 26 questions et le
> comportement observé pour chacune, est dans [GUIDE-DEMONSTRATION.md](GUIDE-DEMONSTRATION.md).**
> La preuve machine correspondante est dans
> [`evidence/demonstration-web.json`](evidence/demonstration-web.json).

Depuis la racine du dépôt :

```powershell
.\.venv\Scripts\python.exe scripts\ingest_corpus.py
.\.venv\Scripts\python.exe scripts\evaluate_rag.py
.\.venv\Scripts\python.exe scripts\rag_cli.py search "REF-8842" --profile support
.\.venv\Scripts\python.exe scripts\rag_cli.py ask "Quelle est la tension assignée du produit REF-8842 ?" --profile support
.\.venv\Scripts\python.exe scripts\rag_cli.py ask "Quelle est la politique de télétravail chez Sorabel ?" --profile support
```

Puis, avec PostgreSQL Sorabel disponible :

```powershell
.\.venv\Scripts\python.exe scripts\setup_postgres.py
.\.venv\Scripts\python.exe scripts\sql_cli.py ask "combien de commandes en avril ?" --profile commercial
.\.venv\Scripts\python.exe scripts\sql_cli.py ask "supprime les commandes de test" --profile commercial
.\.venv\Scripts\python.exe scripts\sql_cli.py ask "quelle est la marge de REF-8842 ?" --profile support
.\.venv\Scripts\python.exe scripts\evaluate_sql.py
```

Serveur et interface :

```powershell
$env:SORABEL_PROFILE = "support"
.\.venv\Scripts\python.exe -m mcp_server.server
.\.venv\Scripts\uvicorn.exe web_app.server:app --host 127.0.0.1 --port 8780
```

## Acceptance et qualité

```powershell
.\.venv\Scripts\pytest.exe tests\acceptance -q --basetemp=.test-tmp\acceptance -p no:cacheprovider
.\.venv\Scripts\pytest.exe tests -q --basetemp=.test-tmp\full -p no:cacheprovider
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe ingest retrieval sql mcp_server application web_app
```

Les métriques annoncées doivent toujours être confirmées par une exécution récente. Les copies
versionnées dans `evidence/` servent à rendre la remise lisible et auditable.

## Limites déclarées

- le générateur SQL déterministe est celui démontré ; l’adaptateur OpenAI-compatible doit être
  évalué avant activation ;
- l’embedding dense local reproductible et `IdentityReranker` constituent le chemin vérifié ;
- le filtrage de `tools/list` par profil est fait (2026-09-04) ; **Keycloak reste à industrialiser** ;
- le profil du prototype MCP est fourni par `SORABEL_PROFILE`, puis chaque appel est réautorisé.
