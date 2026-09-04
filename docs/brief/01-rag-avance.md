# Chantier 1 — RAG avancé

## Demande du brief

1. Normaliser le corpus PDF, HTML et Markdown.
2. Gérer versions, doublons, chunks et métadonnées : titre, référence produit, version et date.
3. Indexer les chunks et fournir une recherche dense avec citations et refus hors corpus.
4. Ajouter BM25, fusion et reranking pour la recherche hybride.
5. Mesurer le gain sur `eval/questions_rag.jsonl`, notamment pour `REF-8842`.

## Réalisation

| Besoin | Code principal | Preuve |
|---|---|---|
| Normalisation | [`ingest/parsers.py`](../../ingest/parsers.py) | [`ingestion-manifest.json`](../livrable/evidence/ingestion-manifest.json) |
| Versions et doublons | [`ingest/catalog.py`](../../ingest/catalog.py) | tests unitaires et manifeste |
| Chunks traçables | [`ingest/chunking.py`](../../ingest/chunking.py) | [modèle de chunks](../livrable/conception/02-modele-chunks-metadonnees.md) |
| Dense + BM25 + RRF | [`retrieval/`](../../retrieval/) | [`rapport_gain.md`](../../eval/rapport_gain.md) |
| Citations et refus | [`retrieval/service.py`](../../retrieval/service.py) | [`test_rag.py`](../../tests/acceptance/test_rag.py) |
| Tools RAG | [`mcp_server/server.py`](../../mcp_server/server.py) | `answer_question`, `search_docs`, `get_document`, `list_sources` |

## Critères d’acceptance couverts

- une question couverte renvoie une réponse avec titre, référence et date ;
- une question hors corpus renvoie `hors_corpus` sans fabrication ;
- `REF-8842` fait remonter la fiche technique en tête ;
- le gain dense → hybride est mesuré et documenté.

La conception globale se lit dans le [schéma de flux](../livrable/conception/01-schema-flux-complet.md).
