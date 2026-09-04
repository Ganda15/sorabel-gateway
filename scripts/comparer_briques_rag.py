"""Compare les trois configurations de recherche, et mesure leur stabilité.

Le brief impose « indexation dans Chroma » et « hybride + reranking », puis
« le gain mesuré, preuve chiffrée à l'appui ». Ces deux exigences se
contredisent si l'index n'est pas reproductible : ce script le montre.

    uv run python scripts/comparer_briques_rag.py

Produit `docs/livrable/evidence/comparaison-briques-rag.json`.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from retrieval.evaluation import evaluate_retrieval  # noqa: E402
from retrieval.service import build_local_service  # noqa: E402


PREUVE = ROOT / "docs/livrable/evidence/comparaison-briques-rag.json"
#: Nombre de constructions par configuration : une seule ne dit rien sur la
#: stabilité, et c'est précisément la stabilité qu'on veut prouver.
ESSAIS = 3

CONFIGURATIONS = (
    ("local", "identity", "Sans reranking — la référence, pour mesurer ce qu'il apporte."),
    ("local", "lexical", "DÉFAUT LIVRÉ — index déterministe + reranking lexical."),
    ("chroma", "lexical", "Chroma, exigé par le brief. Index HNSW approximatif."),
    ("local", "cross_encoder", "Reranking par cross-encoder — le plus fin, le plus lent."),
)


def mesurer(dense: str, reranker: str) -> dict[str, Any]:
    questions = [
        json.loads(ligne)
        for ligne in (ROOT / "eval/questions_rag.jsonl").read_text(encoding="utf-8").splitlines()
        if ligne.strip()
    ]
    essais = []
    for _ in range(ESSAIS):
        debut = time.perf_counter()
        service = build_local_service(ROOT / "data/corpus", ROOT / "data/index", dense, reranker)
        d = evaluate_retrieval(service, questions, "dense")
        h = evaluate_retrieval(service, questions, "hybrid")
        essais.append({
            "dense_recall_at_1": round(d.recall_at_1, 4),
            "hybride_recall_at_1": round(h.recall_at_1, 4),
            "questions_evaluees": d.total,
            "duree_ms": int((time.perf_counter() - debut) * 1000),
            "briques_reelles": service.briques.describe(),
        })

    hybrides = {e["hybride_recall_at_1"] for e in essais}
    return {
        "dense_demande": dense,
        "reranker_demande": reranker,
        "essais": essais,
        "reproductible": len(hybrides) == 1,
        "hybride_valeurs_observees": sorted(hybrides),
    }


def conclure(resultats: list[dict]) -> str:
    """Deduit la conclusion des mesures, au lieu de la figer dans le code.

    La version precedente etait une phrase ecrite a la main. Elle affirmait que
    l'index local etait << le seul des trois >> a etre reproductible. Le jour ou
    une quatrieme configuration est apparue et ou les quatre sont devenues
    reproductibles, la preuve s'est mise a mentir -- et trois documents ont
    recopie ce mensonge. Une conclusion deduite ne peut plus contredire le
    tableau qu'elle resume.
    """
    def nom(mesure: dict) -> str:
        return f"{mesure['dense_demande']} + {mesure['reranker_demande']}"

    def score(mesure: dict) -> float:
        return max(e["hybride_recall_at_1"] for e in mesure["essais"])

    def duree(mesure: dict) -> int:
        durees = sorted(e["duree_ms"] for e in mesure["essais"])
        return durees[len(durees) // 2]

    meilleur = max(score(m) for m in resultats)
    ex_aequo = [m for m in resultats if score(m) == meilleur]
    livre = min(ex_aequo, key=duree)
    instables = [m for m in resultats if not m["reproductible"]]

    phrases = [
        f"Meilleur Recall@1 hybride : {meilleur:.4f}, atteint par "
        f"{len(ex_aequo)} configuration(s) : {', '.join(nom(m) for m in ex_aequo)}.",
        f"La configuration livree est {nom(livre)} : a egalite de score, c'est la plus "
        f"rapide ({duree(livre)} ms contre "
        f"{', '.join(str(duree(m)) + ' ms' for m in ex_aequo if m is not livre) or 'aucune autre'}).",
    ]

    if instables:
        phrases.append(
            "Non reproductible(s) : "
            + ", ".join(f"{nom(m)} ({m['hybride_valeurs_observees']})" for m in instables)
            + ". Le brief demande une preuve chiffree ; un gain qui change d'une "
            "execution a l'autre n'en est pas une."
        )
    else:
        phrases.append(
            f"Les {len(resultats)} configurations donnent la meme valeur aux "
            f"{len(resultats[0]['essais'])} essais : aucune n'est ecartee pour "
            "irreproductibilite."
        )

    ecartes = [m for m in resultats if m is not livre]
    if ecartes:
        phrases.append(
            "Ecartees : "
            + " ; ".join(
                f"{nom(m)} ({score(m):.4f}, {duree(m)} ms)" for m in ecartes
            )
            + ". Toutes restent activables par SORABEL_DENSE_BACKEND et SORABEL_RERANKER."
        )

    # Une couche dense instable derriere un resultat final stable : a dire, car
    # le reranking la masque sans la corriger.
    for mesure in resultats:
        denses = {e["dense_recall_at_1"] for e in mesure["essais"]}
        if len(denses) > 1:
            phrases.append(
                f"A noter : la couche dense de {nom(mesure)} varie "
                f"({sorted(denses)}) alors que son resultat final ne varie pas. "
                "Le reranking absorbe cette instabilite, il ne la supprime pas."
            )

    return " ".join(phrases)

def main() -> int:
    resultats = []
    print(f"{'configuration':<32} {'hybride R@1 (3 essais)':<28} {'reproductible':<14} temps")
    print("-" * 88)
    for dense, reranker, note in CONFIGURATIONS:
        mesure = mesurer(dense, reranker)
        mesure["note"] = note
        resultats.append(mesure)
        valeurs = " ".join(f"{e['hybride_recall_at_1']:.4f}" for e in mesure["essais"])
        moyenne = sum(e["duree_ms"] for e in mesure["essais"]) // ESSAIS
        marque = "oui" if mesure["reproductible"] else "NON"
        print(f"{dense + ' + ' + reranker:<32} {valeurs:<28} {marque:<14} {moyenne} ms")
        print(f"    {note}")

    preuve = {
        "genere_le": datetime.now(timezone.utc).isoformat(),
        "essais_par_configuration": ESSAIS,
        "configurations": resultats,
        "conclusion": conclure(resultats),
    }
    PREUVE.parent.mkdir(parents=True, exist_ok=True)
    PREUVE.write_text(json.dumps(preuve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\npreuve  {PREUVE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
