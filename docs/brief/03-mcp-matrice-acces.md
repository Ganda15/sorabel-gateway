# Chantier 3 — Serveur MCP et matrice d’accès

## Demande du brief

1. Un même serveur MCP expose huit tools à Support, Commercial et Developer.
2. Les droits portent sur les tools, les collections documentaires et les tables/colonnes SQL.
3. `tools/list` et chaque appel doivent respecter le profil ; chaque service réapplique son périmètre.
4. Les refus et erreurs restent des réponses typées, jamais des réponses métier.
5. Tous les appels autorisés ou refusés sont audités.

## Catalogue

| Famille | Tools |
|---|---|
| RAG | `answer_question`, `search_docs`, `get_document`, `list_sources` |
| SQL | `ask_database`, `get_schema`, `check_stock`, `order_status` |

Le catalogue détaillé des entrées, sorties et garanties est dans
[03-catalogue-tools-mcp.md](../livrable/conception/03-catalogue-tools-mcp.md).

## Matrice implémentée

| Profil | answer | search | document | sources | ask DB | schema | stock | order |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Support | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Commercial | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Developer | — | ✓ | ✓ | ✓ | — | ✓ | — | — |

La matrice complète inclut aussi collections et ressources SQL dans
[05-matrice-acces.md](../livrable/conception/05-matrice-acces.md).

## Enforcement et preuves

| Frontière | Responsabilité |
|---|---|
| [`application/gateway.py`](../../application/gateway.py) | autorise le tool selon le profil |
| [`retrieval/service.py`](../../retrieval/service.py) | filtre les collections avant retrieval |
| [`sql/semantic_catalog.json`](../../sql/semantic_catalog.json) | limite vues, colonnes, relations et KPI visibles |
| PostgreSQL | applique rôles, `GRANT SELECT` et transactions read-only |
| [`mcp_server/server.py`](../../mcp_server/server.py) | expose les contrats, route et journalise |
| [`tests/acceptance/test_mcp.py`](../../tests/acceptance/test_mcp.py) | vérifie appels autorisés, refus et audit |

## Limite annoncée honnêtement

Le filtrage natif de `tools/list` par profil est **fait** depuis le 2026-09-04 : support 7 tools,
commercial 8, developer 4 — vérifié par `tests/integration/test_mcp_catalogue.py`. Chaque appel
est en outre réautorisé.

**Keycloak reste une étape d’industrialisation** : le profil est lu dans `SORABEL_PROFILE`, une
variable du processus, pas dans un jeton signé. Ce n’est pas une fonction déjà revendiquée.
