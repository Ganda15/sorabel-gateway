#!/usr/bin/env bash
# Demarrage du conteneur "app" : met les donnees en place, puis sert l'interface.
#
# Chaque etape est rejouable : la base SQLite est regeneree a l'identique (graine
# fixe), l'index est reconstruit, les migrations sont en IF NOT EXISTS et
# l'import PostgreSQL est un upsert. Redemarrer le conteneur ne casse rien.
set -euo pipefail
cd /app

echo "[1/4] base SQLite de reference (deterministe)"
rm -f data/sorabel.db
python scripts/seed.py

echo "[2/4] index documentaire (embedder local, aucun telechargement)"
python scripts/ingest_corpus.py --output data/index

echo "[3/4] PostgreSQL : attente, migrations, import"
python - <<'PY'
import os, time, psycopg
dsn = os.environ["SORABEL_SQL_ADMIN_DSN"]
for essai in range(30):
    try:
        psycopg.connect(dsn, connect_timeout=3).close()
        print("      postgres joignable")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"      attente postgres ({essai + 1}/30) : {type(exc).__name__}")
        time.sleep(2)
else:
    raise SystemExit("postgres injoignable apres 60 s")
PY
python scripts/setup_postgres.py --migrate --import

echo "[4/4] interface web sur 0.0.0.0:8780"
exec uvicorn web_app.server:app --host 0.0.0.0 --port 8780 --proxy-headers --forwarded-allow-ips="*"
