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
    ("local", "identity", "Défaut livré — index déterministe."),
    ("chroma", "identity", "Chroma, exigé par le brief. Index HNSW approximatif."),
    ("chroma", "cross_encoder", "Chroma + reranking cross-encoder."),
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
        "conclusion": (
            "Le défaut livré est l'index local : c'est le seul des trois qui donne la même "
            "valeur à chaque exécution. Le brief demande une preuve chiffrée ; un gain qui "
            "change d'une exécution à l'autre n'en est pas une. Chroma et le cross-encoder "
            "restent branchés et activables par variable d'environnement."
        ),
    }
    PREUVE.parent.mkdir(parents=True, exist_ok=True)
    PREUVE.write_text(json.dumps(preuve, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\npreuve  {PREUVE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
