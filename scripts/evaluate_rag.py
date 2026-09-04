from __future__ import annotations

import json
from pathlib import Path

from retrieval.evaluation import evaluate_retrieval, render_report
from retrieval.service import build_local_service


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    questions = [
        json.loads(line)
        for line in (root / "eval/questions_rag.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    service = build_local_service(root / "data/corpus", root / "data/index")
    dense = evaluate_retrieval(service, questions, "dense")
    hybrid = evaluate_retrieval(service, questions, "hybrid")
    report = render_report(dense, hybrid)
    (root / "eval/rapport_gain.md").write_text(report, encoding="utf-8")
    results = {"dense": dense.__dict__, "hybrid": hybrid.__dict__}
    (root / "eval/resultats_rag.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(report)
    return 0 if hybrid.recall_at_1 > dense.recall_at_1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
