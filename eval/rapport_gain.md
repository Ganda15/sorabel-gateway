# Rapport de gain — RAG avancé Sorabel

Mesure produite automatiquement sur `eval/questions_rag.jsonl`.

| Mode | Recall@1 | MRR | reference_exacte Recall@1 |
|---|---:|---:|---:|
| Dense | 0.727 | 0.774 | 0.750 |
| Hybride (dense + BM25 + RRF) | 0.818 | 0.864 | 0.875 |

- Gain absolu Recall@1 : **9.1 points**
- Gain relatif Recall@1 : **12.5 %**
- Questions évaluées : **22**

Le corpus est interrogé avec le profil `support`; les notes internes sont donc exclues. Le reranker configuré dans ce prototype est déterministe (`IdentityReranker`). Un cross-encoder local peut être activé ultérieurement sans modifier le contrat du service.
