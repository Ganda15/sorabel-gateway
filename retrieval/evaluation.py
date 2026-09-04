from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from retrieval.service import RagService


@dataclass
class EvaluationMetrics:
    total: int = 0
    correct: int = 0
    reciprocal_rank_sum: float = 0.0
    exact_total: int = 0
    exact_correct: int = 0

    @property
    def recall_at_1(self) -> float:
        return self.correct / self.total if self.total else 0.0

    @property
    def mrr(self) -> float:
        return self.reciprocal_rank_sum / self.total if self.total else 0.0

    @property
    def exact_recall_at_1(self) -> float:
        return self.exact_correct / self.exact_total if self.exact_total else 0.0


def _matches(hit, question: dict) -> bool:
    if question.get("attendu_reference"):
        return hit.reference == question["attendu_reference"]
    return hit.doc_type == question.get("attendu_type")


def evaluate_retrieval(service: RagService, questions: Iterable[dict], mode: str) -> EvaluationMetrics:
    metrics = EvaluationMetrics()
    for question in questions:
        if question["type"] == "hors_corpus":
            continue
        hits = service.search_docs(question["question"], "support", limit=5, mode=mode)
        metrics.total += 1
        if question["type"] == "reference_exacte":
            metrics.exact_total += 1
        matching_rank = next((rank for rank, hit in enumerate(hits, 1) if _matches(hit, question)), None)
        if matching_rank:
            metrics.reciprocal_rank_sum += 1.0 / matching_rank
        if matching_rank == 1:
            metrics.correct += 1
            if question["type"] == "reference_exacte":
                metrics.exact_correct += 1
    return metrics


def render_report(dense: EvaluationMetrics, hybrid: EvaluationMetrics) -> str:
    gain = (hybrid.recall_at_1 - dense.recall_at_1) * 100
    relative = gain / (dense.recall_at_1 * 100) * 100 if dense.recall_at_1 else 0.0
    return f"""# Rapport de gain — RAG avancé Sorabel

Mesure produite automatiquement sur `eval/questions_rag.jsonl`.

| Mode | Recall@1 | MRR | reference_exacte Recall@1 |
|---|---:|---:|---:|
| Dense | {dense.recall_at_1:.3f} | {dense.mrr:.3f} | {dense.exact_recall_at_1:.3f} |
| Hybride (dense + BM25 + RRF) | {hybrid.recall_at_1:.3f} | {hybrid.mrr:.3f} | {hybrid.exact_recall_at_1:.3f} |

- Gain absolu Recall@1 : **{gain:.1f} points**
- Gain relatif Recall@1 : **{relative:.1f} %**
- Questions évaluées : **{hybrid.total}**

Le corpus est interrogé avec le profil `support`; les notes internes sont donc exclues. Le reranker configuré dans ce prototype est déterministe (`IdentityReranker`). Un cross-encoder local peut être activé ultérieurement sans modifier le contrat du service.
"""
