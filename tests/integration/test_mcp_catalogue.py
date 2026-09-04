"""Le catalogue MCP annoncé — `tools/list` — respecte la matrice.

La suite d'acceptance fournie vérifie qu'un appel non autorisé est *refusé*.
Elle ne vérifie pas ce que le serveur *annonce*. Or le dossier de conception du
chantier 3 demande explicitement, test n° 1 :

    « Support voit sept tools ; get_schema est absent de tools/list. »

Ces tests couvrent cet écart. Ils lancent un vrai serveur en sous-processus,
comme un client externe : rien n'est importé de l'implémentation.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from application import policy
from tests.conftest import CALL_TIMEOUT, REPO_ROOT, SERVER_MODULE, read_journal


async def _catalogue(profile: str) -> list[tuple[str, str]]:
    """(nom, description) des tools annoncés à ce profil."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULE],
        env={**os.environ, "SORABEL_PROFILE": profile},
        cwd=str(REPO_ROOT),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), CALL_TIMEOUT)
            listed = await asyncio.wait_for(session.list_tools(), CALL_TIMEOUT)
            return [(t.name, t.description or "") for t in listed.tools]


@pytest.mark.parametrize("profile", ["support", "commercial", "developer"])
async def test_le_catalogue_annonce_exactement_les_tools_du_profil(profile: str) -> None:
    annonces = {nom for nom, _ in await _catalogue(profile)}
    assert annonces == policy.tools_by_profile()[profile]


async def test_le_support_ne_voit_pas_get_schema_dans_le_catalogue() -> None:
    # Test n° 1 du dossier de conception, chantier 3.
    annonces = {nom for nom, _ in await _catalogue("support")}
    assert len(annonces) == 7
    assert "get_schema" not in annonces


async def test_chaque_tool_annonce_est_livre_avec_sa_description() -> None:
    """Sans description, aucun agent ne peut choisir : le catalogue serait inutilisable."""
    for nom, description in await _catalogue("commercial"):
        assert description.strip(), f"{nom} est annoncé sans description"
        assert description == policy.describe(nom)


async def test_un_tool_hors_catalogue_reste_refuse_et_journalise(tmp_path: Path) -> None:
    """Cacher un tool ne suffit pas : la matrice est réappliquée à l'appel."""
    journal = tmp_path / "journal.jsonl"
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULE],
        env={**os.environ, "SORABEL_PROFILE": "support", "GATEWAY_JOURNAL": str(journal)},
        cwd=str(REPO_ROOT),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), CALL_TIMEOUT)
            result = await asyncio.wait_for(
                session.call_tool("get_schema", {}), CALL_TIMEOUT
            )

    # Une erreur de protocole ne serait pas journalisée : la réponse doit être
    # une enveloppe métier typée.
    assert not result.isError
    enveloppe = json.loads(result.content[0].text)
    assert enveloppe["status"] == "refused"
    assert enveloppe["payload"]["error_code"] == "NOT_AUTHORIZED"

    entrees = read_journal(journal)
    assert [
        (e["tool"], e["status"], e["error_code"]) for e in entrees
    ] == [("get_schema", "refused", "NOT_AUTHORIZED")]
