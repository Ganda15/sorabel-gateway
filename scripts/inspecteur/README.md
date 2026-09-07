# Vérifier le catalogue MCP avec le client officiel

Ces trois scripts lancent le serveur `mcp_server/` sur un profil donné, pour le
**MCP Inspector** — le client de référence publié par Model Context Protocol.

Pourquoi ils existent : le filtrage du catalogue par profil est visible dans
l'interface web du produit, mais l'interface est *notre* code. L'Inspector, lui,
est un client tiers : ce qu'il affiche est ce que **le protocole** annonce, pas ce
que notre interface veut bien montrer.

## Lancer

Depuis n'importe quel dossier (les scripts se repèrent seuls, via `%~dp0`) :

    npx -y @modelcontextprotocol/inspector scripts\inspecteur\mcp-support.cmd

L'interface web s'ouvre. Onglet **Tools** pour le catalogue, panneau **Protocol**
pour les échanges `initialize` / `tools/list` / `tools/call` chronométrés.

Sans interface, en une ligne :

    npx -y @modelcontextprotocol/inspector --cli scripts\inspecteur\mcp-support.cmd --method tools/list

## Ce qu'on doit voir

| Profil | Tools | `get_schema` |
|---|---|---|
| `support` | **7** | absent |
| `commercial` | **8** | présent |
| `developer` | **4** | présent |

`developer` a `get_schema` mais **aucun** outil métier ; `support` a les outils
métier mais **pas** `get_schema`. Les profils ne s'emboîtent pas : ils se croisent.

## La démonstration en deux appels

Même question, même serveur, deux profils — onglet **Tools → `answer_question`** :

    quelle est la marge sur la REF-8842 ?

| Profil | Réponse |
|---|---|
| `support` | `hors_corpus` — la note tarifaire n'est pas dans ses collections |
| `commercial` | `ok`, avec la source *Point politique tarifaire*, REF-8842 |

## Prérequis

Node (pour `npx`) et le `.venv` du projet installé. PostgreSQL n'est pas nécessaire
pour ces deux appels : `answer_question` ne touche pas la base.
