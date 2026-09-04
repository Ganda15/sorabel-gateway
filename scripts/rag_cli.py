from __future__ import annotations

import argparse
import json
from pathlib import Path

from retrieval.service import build_local_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the local Sorabel Advanced RAG service.")
    parser.add_argument("command", choices=["search", "ask", "sources", "document"])
    parser.add_argument("value", nargs="?", default="")
    parser.add_argument("--profile", choices=["support", "commercial"], default="support")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--mode", choices=["dense", "hybrid"], default="hybrid")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    service = build_local_service(root / "data/corpus", root / "data/index")

    if args.command == "search":
        if not args.value.strip():
            parser.error("search requires a query")
        result = {
            "status": "ok",
            "payload": {"hits": [h.to_payload() for h in service.search_docs(args.value, args.profile, args.limit, args.mode)]},
            "message": "",
        }
    elif args.command == "ask":
        if not args.value.strip():
            parser.error("ask requires a question")
        result = service.answer_question(args.value, args.profile).to_envelope()
    elif args.command == "sources":
        result = {
            "status": "ok",
            "payload": {"sources": [d.model_dump(exclude={"text", "content_hash", "family_id"}) for d in service.list_sources(args.profile)]},
            "message": "",
        }
    else:
        if not args.value.strip():
            parser.error("document requires a document identifier")
        document = service.get_document(args.value, args.profile)
        result = {"status": "ok", "payload": document.model_dump(), "message": ""}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
