# Rapport de gain — RAG avancé Sorabel

Mesure produite automatiquement sur `eval/questions_rag.jsonl`.

| Mode | Recall@1 | MRR | reference_exacte Recall@1 |
|---|---:|---:|---:|
| Dense | 0.727 | 0.774 | 0.750 |
| Hybride (dense + BM25 + RRF) | 0.864 | 0.886 | 1.000 |

- Gain absolu Recall@1 : **13.6 points**
- Gain relatif Recall@1 : **18.7 %**
- Questions évaluées : **22**

Le corpus est interrogé avec le profil `support` : les notes internes sont donc exclues. La chaîne mesurée est dense + BM25, fusion RRF, puis **reranking lexical** — `LexicalReranker`, déterministe et sans réseau. Un cross-encoder est disponible (`SORABEL_RERANKER=cross_encoder`) : mesuré, il donne le **même** Recall@1 pour **26 fois** le temps, et il n'apporte donc rien sur ce corpus. Voir `docs/livrable/evidence/comparaison-briques-rag.json`.
