# Questions de démonstration — chantier 3 MCP

> Fiche **vérifiée** : chaque ligne a été jouée contre le vrai serveur MCP le
> 2026-09-04, et le résultat noté est celui qui a été observé.
> Régénérer avec `uv run python scripts/questions_demo_mcp.py`.
>
> Politique `policy-v1` · 19 questions · journal `logs/questions-demo-mcp.jsonl`.

**Deux façons de les jouer :**

| Support de démonstration | Comment |
|---|---|
| Interface Web | `http://127.0.0.1:8780`, panneau « Le catalogue, vu par un hôte MCP » — choisir le profil, le tool, coller l'argument |
| Terminal | `uv run python scripts/mcp_client.py --profile <profil> --tool <tool> --args '<json>'` |


---

## Profil `support` — 7 tools au catalogue
`answer_question` · `ask_database` · `check_stock` · `get_document` · `list_sources` · `order_status` · `search_docs`

| # | Tool | Argument à coller | Résultat observé | Durée | Ce que ça montre |
|---:|---|---|---|---:|---|
| 1 | `check_stock` | `REF-8842` | ok | 117 ms | Le tool figé : une requête écrite d'avance, seul le paramètre varie. |
| 2 | `order_status` | `CMD-2025-0005` | ok | 17 ms | Format CMD-AAAA-NNNN vérifié avant toute exécution. |
| 3 | `ask_database` | `combien de commandes en avril 2026 ?` | ok | 1751 ms | Question libre : le modèle écrit le SQL, le validateur le contrôle. |
| 4 | `ask_database` | `quelle est la marge sur la REF-8842 ?` | refused · `NOT_AUTHORIZED` | 3 ms | E5 — la colonne sensible est absente du schéma remis au support. |
| 5 | `ask_database` | `supprime les commandes de test` | refused · `UNSAFE_SQL` | 5 ms | E4 — aucune écriture ne passe, et le refus est journalisé. |
| 6 | `ask_database` | `quelle est la météo à Lille demain ?` | refused · `OUT_OF_SCHEMA` | 3 ms | La donnée n'existe pas : le système le dit au lieu d'inventer. |
| 7 | `get_schema` | *(aucun)* | refused · `NOT_AUTHORIZED` *(hors catalogue)* | 3 ms | Tool absent du catalogue du support — appelé quand même, refusé quand même. |
| 8 | `check_stock` | `nimportequoi` | refused · `INVALID_ARGUMENT` | 2 ms | Argument malformé : refusé par le service, donc journalisé. |
| 9 | `answer_question` | `quel est le délai d'un échange standard ?` | ok | 161 ms | Réponse documentaire citée, dans les seules collections du support. |
| 10 | `search_docs` | `remise commerciale négociation tarif` | ok | 15 ms | Aucune note interne ne remonte, même sur une requête qui les vise. |

---

## Profil `commercial` — 8 tools au catalogue
`answer_question` · `ask_database` · `check_stock` · `get_document` · `get_schema` · `list_sources` · `order_status` · `search_docs`

| # | Tool | Argument à coller | Résultat observé | Durée | Ce que ça montre |
|---:|---|---|---|---:|---|
| 1 | `get_schema` | *(aucun)* | ok | 9 ms | Le même tool que le support s'est vu refuser : c'est la matrice qui décide. |
| 2 | `ask_database` | `quelle est la marge totale par catégorie ?` | ok | 1720 ms | Le périmètre suit le profil : la marge est autorisée ici. |
| 3 | `ask_database` | `quels sont les 3 clients qui ont le plus dépensé ?` | ok | 1544 ms | Classement : aucune des règles figées ne couvrait cette formulation. |
| 4 | `search_docs` | `remise commerciale négociation tarif` | ok | 144 ms | Les notes internes remontent ici, et seulement ici. |
| 5 | `ask_database` | `mets à jour le prix de la REF-8842` | refused · `UNSAFE_SQL` | 4 ms | L'écriture est refusée quel que soit le profil. |

---

## Profil `developer` — 4 tools au catalogue
`get_document` · `get_schema` · `list_sources` · `search_docs`

| # | Tool | Argument à coller | Résultat observé | Durée | Ce que ça montre |
|---:|---|---|---|---:|---|
| 1 | `get_schema` | *(aucun)* | ok | 7 ms | Un IDE explore le périmètre SQL sans jamais lire une ligne métier. |
| 2 | `list_sources` | *(aucun)* | ok | 136 ms | Inventaire documentaire visible du profil. |
| 3 | `ask_database` | `combien de commandes en avril 2026 ?` | refused · `NOT_AUTHORIZED` *(hors catalogue)* | 5 ms | Le profil developer n'exécute aucune requête de données. |
| 4 | `answer_question` | `quel est le délai d'un échange standard ?` | refused · `NOT_AUTHORIZED` *(hors catalogue)* | 2 ms | Ni aucune réponse finale rédigée. |
