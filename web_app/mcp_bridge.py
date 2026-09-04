"""Pont entre l'interface Web et le vrai serveur MCP.

⚠️ Ce module ne **simule** rien. Chaque appel lance `python -m mcp_server.server`
en sous-processus, avec le profil demandé dans `SORABEL_PROFILE`, et dialogue
avec lui par le protocole MCP sur `stdio`. L'interface Web devient donc un
**hôte MCP** au même titre que `scripts/mcp_client.py` ou qu'un IDE.

C'est la seule façon honnête de démontrer le chantier 3 dans un navigateur :
appeler la gateway en direct montrerait la matrice, mais pas le catalogue MCP,
pas `tools/list`, et pas le filtrage par profil — qui sont précisément ce que le
brief demande de prouver.

Le sous-processus écrit dans le **même journal** que l'adaptateur Web
(`logs/journal.jsonl`). Une session de démonstration laisse donc des lignes
`channel: web` et `channel: mcp` côte à côte, dans l'ordre.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from application import policy


ROOT = Path(__file__).resolve().parent.parent
SERVER_MODULE = "mcp_server.server"


def _parametres(profile: str) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULE],
        env={**os.environ, "SORABEL_PROFILE": profile},
        cwd=str(ROOT),
    )


async def catalogue(profile: str) -> dict[str, Any]:
    """`tools/list` réel pour ce profil — ce que l'hôte reçoit, rien de plus."""
    debut = time.perf_counter()
    async with stdio_client(_parametres(profile)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            outils = [
                {
                    "nom": outil.name,
                    "description": outil.description or "",
                    "arguments": sorted((outil.inputSchema or {}).get("properties", {})),
                }
                for outil in listed.tools
            ]
    annonces = {outil["nom"] for outil in outils}
    # Les tools du catalogue officiel que ce profil ne voit PAS. Les afficher
    # rend le filtrage visible : sans eux, on ne voit qu'une liste plus courte.
    absents = [
        {"nom": nom, "description": policy.describe(nom)}
        for nom in policy.all_tools()
        if nom not in annonces
    ]
    return {
        "status": "ok",
        "payload": {
            "profil": profile,
            "tools": outils,
            "nombre": len(outils),
            "absents": absents,
            "catalogue_officiel": len(policy.all_tools()),
        },
        "message": "",
        "duree_ms": int((time.perf_counter() - debut) * 1000),
    }


async def appeler(profile: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """`tools/call` réel. L'enveloppe renvoyée est celle du serveur, non retouchée."""
    debut = time.perf_counter()
    async with stdio_client(_parametres(profile)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            annonces = {outil.name for outil in (await session.list_tools()).tools}
            resultat = await session.call_tool(tool, arguments)

    # `content` est une union : texte, image, audio, lien, ressource. Seul le
    # premier porte `.text` — la gateway ne renvoie que du texte JSON.
    textes = [
        texte
        for bloc in resultat.content
        if isinstance(texte := getattr(bloc, "text", None), str) and texte
    ]
    duree = int((time.perf_counter() - debut) * 1000)

    if resultat.isError or not textes:
        # Une erreur de protocole n'est pas une décision métier : elle n'est pas
        # journalisée. La distinguer explicitement évite de la présenter comme un
        # refus de la matrice.
        return {
            "status": "protocol_error",
            "payload": {"annonce_au_catalogue": tool in annonces},
            "message": textes[0] if textes else "Le serveur MCP n'a renvoyé aucun contenu.",
            "duree_ms": duree,
        }

    try:
        enveloppe = json.loads(textes[0])
    except json.JSONDecodeError:
        return {
            "status": "protocol_error",
            "payload": {},
            "message": textes[0][:500],
            "duree_ms": duree,
        }

    enveloppe.setdefault("payload", {})
    enveloppe.setdefault("message", "")
    enveloppe["duree_ms"] = duree
    # Un tool absent du catalogue mais quand même appelé : c'est le cas qui
    # prouve que le filtrage n'est pas la sécurité, la matrice l'est.
    enveloppe["payload"]["annonce_au_catalogue"] = tool in annonces
    return enveloppe
