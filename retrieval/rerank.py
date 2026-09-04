from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from retrieval.models import SearchHit


class IdentityReranker:
    def rerank(self, query: str, hits: Sequence[SearchHit], limit: int) -> list[SearchHit]:
        del query
        return list(hits[:limit])


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model: Any = None

    def rerank(self, query: str, hits: Sequence[SearchHit], limit: int) -> list[SearchHit]:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        scores = self._model.predict([(query, hit.text) for hit in hits])
        reranked = [hit.model_copy(update={"score": float(score), "rerank_score": float(score)}) for hit, score in zip(hits, scores, strict=True)]
        return sorted(reranked, key=lambda item: (-item.score, item.chunk_id))[:limit]


class LexicalReranker:
    """Reclasse les candidats fusionnés, sans modèle et sans réseau.

    Le brief demande « hybride **+ reranking** ». Le cross-encoder ci-dessus le
    ferait mieux, mais il coûte 7 s au premier appel et fait échouer trois des
    quatre tests d'acceptance — mesuré le 2026-09-04.

    Ce reranker-ci relit chaque candidat **à la lumière de la question**, ce que
    la fusion RRF ne fait pas : RRF ne connaît que des rangs, pas le contenu.
    Trois signaux, du plus fort au plus faible :

    1. la **référence produit** demandée apparaît dans le passage — c'est le
       signal décisif du corpus Sorabel, et celui que le dense rate ;
    2. la **part des mots de la question** couverte par le titre et le texte ;
    3. le rang de fusion, comme départage — un reranker ne doit pas défaire
       gratuitement ce que la fusion a établi.

    Déterministe : mêmes entrées, même sortie, à chaque exécution. C'est ce que
    le brief exige d'un gain « chiffré ».
    """

    #: Poids d'une référence produit trouvée. Volontairement écrasant : sur ce
    #: corpus, une référence exacte n'est jamais une coïncidence.
    POIDS_REFERENCE = 10.0
    #: Poids du recouvrement de termes, entre 0 et 1 avant pondération.
    POIDS_RECOUVREMENT = 3.0

    def rerank(self, query: str, hits: Sequence[SearchHit], limit: int) -> list[SearchHit]:
        from retrieval.tokenization import tokenize

        termes = set(tokenize(query))
        if not termes:
            return list(hits[:limit])

        references = {terme for terme in termes if terme.startswith("ref-")}

        def score(rang: int, hit: SearchHit) -> tuple[float, str]:
            valeur = 0.0
            if references and hit.reference.casefold() in references:
                valeur += self.POIDS_REFERENCE
                # Une fiche technique répond mieux qu'une notice à « REF-8842 ».
                if hit.doc_type == "fiche_technique":
                    valeur += 1.0
            mots = set(tokenize(f"{hit.title} {hit.reference} {hit.text}"))
            if mots:
                valeur += self.POIDS_RECOUVREMENT * len(termes & mots) / len(termes)
            # Le rang de fusion départage, sans jamais dominer les deux signaux.
            valeur += 1.0 / (rang + 1)
            return (-valeur, hit.chunk_id)

        classes = sorted(enumerate(hits), key=lambda paire: score(paire[0], paire[1]))
        return [hit for _, hit in classes][:limit]
