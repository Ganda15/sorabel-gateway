# Sorabel development rules

These rules apply to the complete repository.

## Working method

- Preserve `before-rag-development` as the immutable starter baseline.
- Develop the first increment on `feature/rag-avance`.
- Do not modify the supplied acceptance tests to make an implementation pass.
- Use test-driven development: failing test, minimal implementation, refactor, verification.
- Keep commits small enough to demonstrate separately with GitLens.
- Never invent evaluation results. Generate every metric from `eval/questions_rag.jsonl`.

## Delivery order

1. Make Advanced RAG queryable from the terminal.
2. Add a minimal graphical interface early and connect it to the same RAG service.
3. Add Text-to-SQL tools and their tests.
4. Build the MCP Gateway last to expose and govern both services.

## Architecture boundaries

- `ingest/` prepares canonical documents, metadata, versions, chunks and indexes.
- `retrieval/` implements dense search, BM25, RRF, optional reranking, evidence control and citations.
- `sql/` owns Text-to-SQL and read-only database access.
- `mcp_server/` owns tool contracts, authorization, routing and audit; business logic stays in the service modules.
- `scripts/` contains reproducible terminal commands and demo entry points.

## Non-negotiable guarantees

- A covered documentary answer cites title, reference and date.
- Insufficient evidence returns `hors_corpus`; it never fabricates an answer.
- Exact references such as `REF-8842` must benefit from lexical retrieval.
- The dense-to-hybrid gain is measured and documented.
- Sensitive data, authentication and SQL safety requirements remain enforced in their respective later phases.
