"""Le serveur MCP choisit son transport et son adresse d'après l'environnement.

Par défaut il parle `stdio` : un hôte local le lance et lui parle sur ses flux.
Pour être joignable à distance — derrière un reverse-proxy, un profil par
adresse — il doit pouvoir parler `streamable-http` sur un hôte, un port et un
chemin donnés, sans qu'on touche au code.
"""

import pytest

from mcp_server import server


def test_le_transport_par_defaut_reste_stdio():
    assert server.transport_depuis_env({}) == "stdio"


def test_le_transport_http_se_demande_par_l_environnement():
    env = {"SORABEL_MCP_TRANSPORT": "streamable-http"}
    assert server.transport_depuis_env(env) == "streamable-http"


def test_un_transport_inconnu_est_refuse_avec_un_message_clair():
    with pytest.raises(ValueError, match="SORABEL_MCP_TRANSPORT"):
        server.transport_depuis_env({"SORABEL_MCP_TRANSPORT": "telepathie"})


def test_sans_variable_les_reglages_reseau_ne_changent_pas():
    """Rien dans l'environnement : on ne surcharge aucun défaut de la bibliothèque."""
    assert server.parametres_reseau({}) == {}


def test_les_reglages_reseau_viennent_de_l_environnement():
    env = {
        "SORABEL_MCP_HOST": "0.0.0.0",
        "SORABEL_MCP_PORT": "8791",
        "SORABEL_MCP_PATH": "/mcp/support",
    }
    assert server.parametres_reseau(env) == {
        "host": "0.0.0.0",
        "port": 8791,
        "streamable_http_path": "/mcp/support",
        "stateless_http": True,
    }


def test_un_port_qui_n_est_pas_un_nombre_est_refuse():
    with pytest.raises(ValueError, match="SORABEL_MCP_PORT"):
        server.parametres_reseau({"SORABEL_MCP_PORT": "huit-mille"})
