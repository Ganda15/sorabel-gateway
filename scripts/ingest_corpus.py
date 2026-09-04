from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingest.pipeline import ingest_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and chunk the Sorabel document corpus.")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus"))
    parser.add_argument("--output", type=Path, default=Path("data/index"))
    args = parser.parse_args()
    manifest = ingest_corpus(args.corpus, args.output)
    print(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2))
    return 1 if manifest.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
