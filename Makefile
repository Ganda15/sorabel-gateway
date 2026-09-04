.PHONY: install up down seed ingest setup-postgres evaluate evaluate-sql web test fmt lint serve client journal

install:
	uv sync

seed:
	uv run python scripts/seed.py

ingest:
	uv run python scripts/ingest_corpus.py

evaluate:
	uv run python scripts/evaluate_rag.py

setup-postgres:
	uv run python scripts/setup_postgres.py

evaluate-sql:
	uv run python scripts/evaluate_sql.py

web:
	uv run uvicorn web_app.server:app --host 127.0.0.1 --port 8780

up:
	docker compose up -d

down:
	docker compose down

test:
	uv run pytest

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .
	uv run mypy ingest retrieval sql mcp_server

serve:
	uv run python -m mcp_server.server

client:
	uv run python scripts/mcp_client.py --profile $${PROFILE:-support}

journal:
	@tail -n 20 logs/journal.jsonl 2>/dev/null || echo "journal vide"
