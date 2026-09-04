"""L'interface Web est un vrai hôte MCP — pas une imitation.

Ces tests lancent l'application FastAPI, qui lance à son tour un vrai serveur
MCP en sous-processus. S'ils passent, c'est que le navigateur voit exactement ce
qu'un IDE verrait : le même catalogue, les mêmes refus, le même journal.

Le piège qu'ils ferment : une interface qui appellerait la gateway en direct
afficherait la matrice, mais ne prouverait rien sur MCP — ni `tools/list`, ni le
filtrage par profil. Ce serait un écran qui raconte le chantier au lieu de le
démontrer.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from application import audit, policy
from web_app.server import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("profile", ["support", "commercial", "developer"])
def test_le_catalogue_web_est_celui_du_serveur_mcp(client: TestClient, profile: str) -> None:
    reponse = client.post("/api/mcp/catalogue", json={"profile": profile})
    assert reponse.status_code == 200

    payload = reponse.json()["payload"]
    annonces = {outil["nom"] for outil in payload["tools"]}
    assert annonces == policy.tools_by_profile()[profile]
    assert payload["catalogue_officiel"] == len(policy.all_tools())

    # Les tools absents sont renvoyés eux aussi : sans eux, l'écran montrerait
    # une liste plus courte sans dire ce qui manque ni pourquoi.
    absents = {outil["nom"] for outil in payload["absents"]}
    assert annonces | absents == set(policy.all_tools())
    assert annonces & absents == set()


def test_le_support_ne_voit_pas_get_schema_dans_l_interface(client: TestClient) -> None:
    payload = client.post("/api/mcp/catalogue", json={"profile": "support"}).json()["payload"]
    assert payload["nombre"] == 7
    assert [outil["nom"] for outil in payload["absents"]] == ["get_schema"]


def test_chaque_tool_annonce_porte_la_description_de_la_politique(client: TestClient) -> None:
    payload = client.post("/api/mcp/catalogue", json={"profile": "commercial"}).json()["payload"]
    for outil in payload["tools"]:
        assert outil["description"] == policy.describe(outil["nom"])


def test_un_tool_hors_matrice_est_refuse_et_signale_comme_hors_catalogue(
    client: TestClient,
) -> None:
    enveloppe = client.post(
        "/api/mcp/call",
        json={"profile": "support", "tool": "get_schema", "arguments": {}},
    ).json()

    assert enveloppe["status"] == "refused"
    assert enveloppe["payload"]["error_code"] == "NOT_AUTHORIZED"
    # Le drapeau qui porte la démonstration : le tool n'était pas annoncé, il a
    # été appelé quand même, et la matrice l'a refusé.
    assert enveloppe["payload"]["annonce_au_catalogue"] is False


def test_le_meme_tool_est_autorise_au_commercial(client: TestClient) -> None:
    enveloppe = client.post(
        "/api/mcp/call",
        json={"profile": "commercial", "tool": "get_schema", "arguments": {}},
    ).json()
    assert enveloppe["status"] == "ok"
    assert enveloppe["payload"]["annonce_au_catalogue"] is True


def test_un_argument_invalide_est_refuse_par_le_service_pas_par_le_protocole(
    client: TestClient,
) -> None:
    """Un refus protocolaire échapperait au journal : E5 exige l'inverse."""
    enveloppe = client.post(
        "/api/mcp/call",
        json={"profile": "support", "tool": "check_stock", "arguments": {"reference": "xxx"}},
    ).json()
    assert enveloppe["status"] == "refused"
    assert enveloppe["payload"]["error_code"] == "INVALID_ARGUMENT"


def test_un_tool_hors_catalogue_officiel_est_rejete_avant_tout_sous_processus(
    client: TestClient,
) -> None:
    reponse = client.post(
        "/api/mcp/call",
        json={"profile": "support", "tool": "drop_database", "arguments": {}},
    )
    assert reponse.status_code == 400
    assert reponse.json()["status"] == "invalid_request"


def test_le_journal_expose_les_deux_canaux(client: TestClient, tmp_path: Path) -> None:
    client.post(
        "/api/mcp/call",
        json={"profile": "support", "tool": "check_stock", "arguments": {"reference": "REF-8842"}},
    )
    reponse = client.get("/api/mcp/journal?limit=20")
    assert reponse.status_code == 200

    entrees = reponse.json()["payload"]["entrees"]
    assert entrees, "le journal ne doit pas être vide après un appel"
    assert entrees[-1]["channel"] == "mcp"
    assert set(entrees[-1]) >= {"channel", "profile", "tool", "status", "error_code"}


def test_le_journal_borne_le_nombre_de_lignes_demandees(client: TestClient) -> None:
    """Une limite non bornée ferait renvoyer tout le journal à chaque appel."""
    entrees = client.get("/api/mcp/journal?limit=1000").json()["payload"]["entrees"]
    assert len(entrees) <= 100
    assert len(entrees) <= len(audit.read_entries())
