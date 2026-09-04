# Mini-guide d’accès à la Sorabel Data Gateway

## Préparer l’environnement

Depuis la racine du dépôt :

```powershell
uv sync --extra vector
uv run python scripts/seed.py
uv run python scripts/ingest_corpus.py
docker compose up -d postgres
uv run python scripts/setup_postgres.py
```

La configuration locale sensible reste dans `.env`, jamais dans Git.

## Démarrer le serveur MCP

Le transport de démonstration est `stdio`. Le profil est attaché au processus :

```powershell
$env:SORABEL_PROFILE = "support"
uv run python -m mcp_server.server
```

Il est généralement plus simple d’utiliser le client de démonstration, qui lance le serveur avec
le bon profil :

```powershell
uv run python scripts/mcp_client.py --profile support --tool search_docs --args '{"query":"REF-8842"}'
uv run python scripts/mcp_client.py --profile commercial --tool ask_database --args '{"question":"combien de commandes en avril ?"}'
```

## Profils

- `support` : documents clients, données opérationnelles autorisées, aucune marge ni prix d’achat ;
- `commercial` : huit tools et périmètre métier complet ;
- `developer` : inspection documentaire et schéma, sans réponse finale ni requête de données.

La matrice détaillée se trouve dans `docs/livrable/conception/05-matrice-acces.md`.

## Contrat de réponse

```json
{"status":"ok","payload":{},"message":""}
```

Pour un refus, une clarification, un hors-corpus ou une erreur, `message` est explicite et
`payload` ne doit pas contenir une réponse métier inventée.

## Journal

Le chemin par défaut est `logs/journal.jsonl`. Pour choisir un autre fichier :

```powershell
$env:GATEWAY_JOURNAL = "logs/demo.jsonl"
```

Le journal contient les succès et les refus. Il ne doit jamais contenir de mot de passe, de token
ou de raisonnement privé.

## Interface Web

```powershell
uv run uvicorn web_app.server:app --host 127.0.0.1 --port 8780
```

Puis ouvrir `http://127.0.0.1:8780`. Sous Windows, `START-SORABEL-UI.bat` lance la même interface.
