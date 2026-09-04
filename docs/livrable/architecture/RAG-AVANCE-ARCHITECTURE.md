# Architecture d’implémentation du RAG avancé

Ce document décrit le RAG réellement intégré dans Sorabel. Les sources Mermaid modifiables et
zoomables sont dans [`diagrams/`](diagrams/).

## 1. Pipeline RAG

```mermaid
flowchart LR
    subgraph SOURCE[Corpus Sorabel]
        PDF[PDF techniques]
        HTML[Procédures HTML]
        MD[Notes Markdown]
    end

    subgraph INGEST[Ingestion]
        PARSE[Parseurs par format]
        CANON[Documents canoniques]
        VERS[Versions et doublons]
        CHUNK[Chunks + métadonnées]
        MANIFEST[Manifeste]
    end

    subgraph INDEX[Index]
        VECTOR[(Dense / Chroma)]
        LEXICAL[(BM25)]
    end

    subgraph RETRIEVAL[Retrieval et preuve]
        RRF[Fusion RRF]
        RERANK[Reranker interchangeable]
        EVIDENCE{Preuve autorisée et suffisante ?}
        ANSWER[Réponse + citations]
        REFUSE[hors_corpus]
    end

    PDF --> PARSE
    HTML --> PARSE
    MD --> PARSE
    PARSE --> CANON --> VERS --> CHUNK
    VERS --> MANIFEST
    CHUNK --> VECTOR --> RRF
    CHUNK --> LEXICAL --> RRF
    RRF --> RERANK --> EVIDENCE
    EVIDENCE -->|oui| ANSWER
    EVIDENCE -->|non| REFUSE
```

Les formats changent, mais le contrat canonique reste identique. Chaque chunk conserve le titre,
la référence, la version, la date, le type documentaire et la collection. Dense traite la
formulation naturelle, BM25 renforce les termes exacts comme `REF-8842`, RRF fusionne les rangs,
puis le contrôle de preuve choisit entre réponse citée et refus.

## 2. Intégration dans la Gateway

```mermaid
flowchart LR
    USERS[Support · Commercial · Developer/IDE]

    subgraph ACCESS[Points d’accès]
        CLI[CLI RAG]
        WEB[Interface Web]
        MCP[Serveur MCP<br/>4 tools RAG]
    end

    GATEWAY[ApplicationGateway<br/>profil · tool · contrat]
    SERVICE[RagService commun<br/>scope · hybrid retrieval · preuve]
    CORPUS[(Corpus autorisé<br/>PDF · HTML · Markdown)]
    OUTPUT[Réponse citée<br/>ou hors_corpus]
    AUDIT[(Audit MCP)]

    USERS --> CLI
    USERS --> WEB
    USERS --> MCP
    CLI --> GATEWAY
    WEB --> GATEWAY
    MCP --> GATEWAY
    GATEWAY --> SERVICE --> CORPUS
    CORPUS --> SERVICE --> OUTPUT
    OUTPUT --> CLI
    OUTPUT --> WEB
    OUTPUT --> MCP --> AUDIT
```

Le terminal, l’interface Web et les quatre tools MCP réutilisent le même `RagService`. Le profil
limite les collections avant la recherche. La logique de citations et de refus n’est donc pas
dupliquée selon le client.

## Code et preuves

| Responsabilité | Code | Preuve |
|---|---|---|
| parsing et contrat canonique | `ingest/parsers.py`, `ingest/models.py` | tests unitaires |
| versions et doublons | `ingest/catalog.py` | manifeste d’ingestion |
| chunks et indexation | `ingest/chunking.py`, `ingest/pipeline.py` | `docs/livrable/evidence/ingestion-manifest.json` |
| dense, BM25 et RRF | `retrieval/dense.py`, `lexical.py`, `fusion.py` | `eval/rapport_gain.md` |
| scope, preuve et citations | `retrieval/service.py` | `tests/acceptance/test_rag.py` |
| CLI, Web et MCP | `scripts/rag_cli.py`, `web_app/`, `mcp_server/server.py` | tests d’intégration et acceptance |

Le chemin vérifié utilise l’embedder local déterministe et `IdentityReranker`. Les adaptateurs
Sentence Transformer et Cross Encoder existent comme extensions, mais aucun gain ne leur est
attribué sans mesure dédiée.
