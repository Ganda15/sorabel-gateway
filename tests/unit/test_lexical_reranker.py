"""Tests du reranking lexical livre par defaut.

Pourquoi ce fichier existe : le `LexicalReranker` est devenu le reranker par
defaut le 2026-09-04, et il deplace les chiffres annonces au formateur
(Recall@1 hybride 0,8182 -> 0,8636, references exactes 0,750 -> 1,000). Une
brique qui change les chiffres du livrable doit avoir ses propres tests, pas
seulement une couverture indirecte par la chaine complete.

Ce qui est verifie ici :
  1. le determinisme, deux fois de suite et sur une entree melangee ;
  2. la remontee d'une reference exacte, meme arrivee derniere de la fusion ;
  3. la preference fiche technique > notice a reference egale (critere 3) ;
  4. le repli quand la question ne donne aucun jeton ;
  5. le respect de `limit`.
"""

from __future__ import annotations

import random

from retrieval.models import SearchHit
from retrieval.rerank import LexicalReranker


def hit(
    chunk_id: str,
    *,
    reference: str = "REF-1",
    doc_type: str = "fiche_technique",
    text: str = "texte",
    title: str = "titre",
    score: float = 1.0,
) -> SearchHit:
    collection = {
        "fiche_technique": "fiches_techniques",
        "notice": "notices",
    }[doc_type]
    return SearchHit(
        chunk_id=chunk_id,
        doc_id=chunk_id,
        score=score,
        text=text,
        title=title,
        reference=reference,
        version="1",
        date="2025-01-01",
        doc_type=doc_type,
        collection=collection,
        source_path=f"{chunk_id}.pdf",
    )


def test_remonte_la_reference_exacte_arrivee_derniere():
    """Le cas que le brief nomme : une question qui cite une reference produit.

    Le bon document arrive ici en DERNIERE position de la fusion. S'il ne
    remonte pas premier, la mesure `reference_exacte Recall@1 = 1,000` est
    fausse.
    """
    hits = [
        hit("a", reference="REF-1000", text="un autre produit"),
        hit("b", reference="REF-2000", text="encore un autre"),
        hit("c", reference="REF-8842", text="la bonne fiche"),
    ]

    classes = LexicalReranker().rerank("caracteristiques de la REF-8842", hits, limit=3)

    assert classes[0].reference == "REF-8842"


def test_fiche_technique_avant_notice_a_reference_egale():
    """Critere d'acceptance 3 : REF-8842 doit remonter la FICHE, pas la notice.

    C'est exactement ce que le cross-encoder cassait.
    """
    hits = [
        hit("notice", reference="REF-8842", doc_type="notice", text="notice REF-8842"),
        hit("fiche", reference="REF-8842", doc_type="fiche_technique", text="fiche REF-8842"),
    ]

    classes = LexicalReranker().rerank("REF-8842", hits, limit=2)

    assert classes[0].doc_type == "fiche_technique"
    assert classes[1].doc_type == "notice"


def test_deterministe_sur_deux_appels():
    """Le brief exige une preuve chiffree. Un classement qui bouge n'en est pas une."""
    hits = [hit(f"c{indice}", reference=f"REF-{indice}") for indice in range(10)]
    reranker = LexicalReranker()

    premier = reranker.rerank("REF-3 documentation technique", hits, limit=5)
    second = reranker.rerank("REF-3 documentation technique", hits, limit=5)

    assert [h.chunk_id for h in premier] == [h.chunk_id for h in second]


def test_a_evidence_lexicale_egale_l_ordre_de_la_fusion_est_conserve():
    """A egalite lexicale, le reranker ne reinvente rien : il garde l'ordre RRF.

    C'est le role du terme `1 / (rang + 1)` dans le score. Ce n'est pas un
    detail : l'ordre entrant vient de la fusion RRF, qui est deterministe, donc
    la chaine entiere le reste. Le reranker ne deplace un candidat que s'il a
    une raison lexicale de le faire.

    Corollaire assume : reclasser une liste melangee donne un autre ordre. Ce
    n'est pas de l'instabilite -- c'est une entree differente.
    """
    hits = [hit(f"c{indice}", reference="REF-9", text="texte identique") for indice in range(8)]

    classes = LexicalReranker().rerank("REF-9", hits, limit=8)

    assert [h.chunk_id for h in classes] == [h.chunk_id for h in hits]

    melange = list(hits)
    random.Random(1789).shuffle(melange)
    reclasse = LexicalReranker().rerank("REF-9", melange, limit=8)

    assert [h.chunk_id for h in reclasse] == [h.chunk_id for h in melange]


def test_question_sans_jeton_rend_les_premiers_candidats_inchanges():
    """Repli explicite : sans terme exploitable, on ne reclasse pas au hasard,
    on garde l'ordre de la fusion."""
    hits = [hit("a"), hit("b"), hit("c")]

    classes = LexicalReranker().rerank("   ", hits, limit=2)

    assert [h.chunk_id for h in classes] == ["a", "b"]


def test_respecte_la_limite():
    hits = [hit(f"c{indice}") for indice in range(6)]

    classes = LexicalReranker().rerank("fiche technique", hits, limit=2)

    assert len(classes) == 2


def test_ne_perd_aucun_candidat_quand_la_limite_les_couvre_tous():
    """Le reranking reclasse ; il ne filtre pas."""
    hits = [hit(f"c{indice}", reference=f"REF-{indice}") for indice in range(5)]

    classes = LexicalReranker().rerank("REF-2", hits, limit=5)

    assert sorted(h.chunk_id for h in classes) == sorted(h.chunk_id for h in hits)
