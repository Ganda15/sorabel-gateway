"""Choix des briques de recherche : index dense et reranker.

Le brief impose deux choses que le service ne faisait pas :

* « indexation dans **Chroma** » — `ingest/chroma_store.py` existait et était
  testé, mais `build_local_service` ne s'en servait pas ;
* « hybride **+ reranking** » — `CrossEncoderReranker` existait, mais le service
  instanciait `IdentityReranker`, qui renvoie les résultats inchangés.

Les deux sont désormais **branchés et sélectionnables**. Ils ne sont pas actifs
par défaut, et cette décision repose sur des mesures, pas sur une préférence.

## Pourquoi Chroma n'est pas le défaut — mesuré le 2026-09-04

Trois constructions successives du même service, même corpus, même encodeur
(l'encodeur, lui, est déterministe : vérifié) :

    essai 1 : dense R@1 0,7273   hybride 0,8182
    essai 2 : dense R@1 0,5000   hybride 0,7727
    essai 3 : dense R@1 0,5000   hybride 0,7727
    → 8 questions sur 22 changent de premier résultat

L'index HNSW de Chroma est **approximatif**. Le brief exige une « preuve
chiffrée à l'appui » : un gain qui change d'une exécution à l'autre n'est pas
une preuve. L'index local, lui, est déterministe et donne 0,8182 à chaque fois.

## Pourquoi le cross-encoder n'est pas le défaut — mesuré le même jour

    tests/acceptance/test_rag.py  →  3 échecs sur 4, dont un par dépassement
    première recherche            →  7 197 ms (chargement du modèle)
    recherches suivantes          →  620 ms, contre 15 ms sans

Le cross-encoder remonte la **notice** au-dessus de la **fiche technique** sur
« REF-8842 », ce que le critère d'acceptance interdit. Et le brief exige que
tous les tests d'acceptance fournis passent.

## Comment activer l'un ou l'autre

    SORABEL_DENSE_BACKEND = chroma | local            (défaut : local)
    SORABEL_RERANKER      = cross_encoder | identity  (défaut : identity)

Le repli n'est jamais silencieux : `describe()` renvoie ce qui tourne vraiment,
et `scripts/comparer_briques_rag.py` rejoue la comparaison ci-dessus.
"""

from __future__ import annotations

import importlib.util
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ingest.models import DocumentChunk
from retrieval.dense import LocalDenseIndex
from retrieval.embeddings import LocalHashEmbedder
from retrieval.models import SearchHit
from retrieval.rerank import IdentityReranker


#: Modèle de cross-encoder par défaut. Petit, multilingue, chargé à la demande.
CROSS_ENCODER_DEFAUT = "cross-encoder/ms-marco-MiniLM-L-6-v2"
#: Dimensions du vecteur local, alignées sur LocalDenseIndex.
DIMENSIONS = 768


class DenseIndex(Protocol):
    def search(self, query: str, limit: int = 20) -> list[SearchHit]: ...


class Reranker(Protocol):
    def rerank(self, query: str, hits: Sequence[SearchHit], limit: int) -> list[SearchHit]: ...


@dataclass(frozen=True)
class Choix:
    """Ce qui tourne réellement, et pourquoi — jamais ce qu'on espérait."""

    dense: str
    reranker: str
    dense_repli: str | None = None
    reranker_repli: str | None = None

    def describe(self) -> dict[str, Any]:
        return {
            "dense": self.dense,
            "reranker": self.reranker,
            "dense_repli": self.dense_repli,
            "reranker_repli": self.reranker_repli,
        }


def _construire_dense(chunks: Sequence[DocumentChunk], demande: str) -> tuple[DenseIndex, str, str | None]:
    if demande != "chroma":
        return LocalDenseIndex(chunks), "local", None
    try:
        import chromadb

        from ingest.chroma_store import ChromaVectorStore

        store = ChromaVectorStore(
            chromadb.EphemeralClient(), LocalHashEmbedder(DIMENSIONS), "sorabel_documents"
        )
        store.upsert(list(chunks))
        return store, "chroma", None
    except Exception as exc:  # noqa: BLE001
        # Chroma est une dépendance lourde : indisponible, le service doit
        # continuer à répondre, mais il doit le dire.
        return LocalDenseIndex(chunks), "local", f"{type(exc).__name__}: {exc}"[:200]


def _construire_reranker(demande: str) -> tuple[Reranker, str, str | None]:
    if demande != "cross_encoder":
        return IdentityReranker(), "identity", None
    # On teste la DISPONIBILITE du paquet sans l'importer : importer
    # sentence_transformers charge torch, mesure 72 s sur cette machine, et le
    # service est construit a chaque session. find_spec est instantane.
    if importlib.util.find_spec("sentence_transformers") is None:
        return IdentityReranker(), "identity", "sentence_transformers absent"
    try:
        from retrieval.rerank import CrossEncoderReranker

        return CrossEncoderReranker(CROSS_ENCODER_DEFAUT), "cross_encoder", None
    except Exception as exc:  # noqa: BLE001
        return IdentityReranker(), "identity", f"{type(exc).__name__}: {exc}"[:200]


def construire(
    chunks: Sequence[DocumentChunk],
    dense_backend: str | None = None,
    reranker: str | None = None,
) -> tuple[DenseIndex, Reranker, Choix]:
    """Renvoie l'index dense, le reranker, et le compte rendu de ce qui tourne."""
    demande_dense = (dense_backend or os.environ.get("SORABEL_DENSE_BACKEND", "local")).lower()
    demande_rerank = (reranker or os.environ.get("SORABEL_RERANKER", "identity")).lower()

    index, nom_dense, repli_dense = _construire_dense(chunks, demande_dense)
    classeur, nom_rerank, repli_rerank = _construire_reranker(demande_rerank)

    return index, classeur, Choix(nom_dense, nom_rerank, repli_dense, repli_rerank)
