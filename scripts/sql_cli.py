from __future__ import annotations

import argparse
import json
from pathlib import Path

from sql.service import build_sql_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the governed Sorabel Text-to-SQL service.")
    parser.add_argument("command", choices=["ask", "schema", "stock", "order"])
    parser.add_argument("value", nargs="?", default="")
    parser.add_argument(
        "--profile",
        choices=["support", "commercial", "developer"],
        default="commercial",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    service = build_sql_service(root)
    try:
        if args.command == "ask":
            if not args.value.strip():
                parser.error("ask requires a business question")
            result = service.ask_database(args.value, args.profile)
        elif args.command == "schema":
            result = service.get_schema(args.profile)
        elif args.command == "stock":
            if not args.value.strip():
                parser.error("stock requires a product reference")
            result = service.check_stock(args.value, args.profile)
        else:
            if not args.value.strip():
                parser.error("order requires an order identifier")
            result = service.order_status(args.value, args.profile)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0 if result.status == "ok" else 2
    finally:
        service.close()


if __name__ == "__main__":
    raise SystemExit(main())
