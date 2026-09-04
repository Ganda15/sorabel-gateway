# Catalogue MCP de la Sorabel Data Gateway — guide des équipes clientes

> Document destiné aux équipes qui **consomment** la gateway : bot, poste métier, IDE,
> script d'intégration. Il décrit le contrat, pas l'implémentation.
>
> Tous les tableaux et toutes les descriptions de cette page sont **générés** depuis
> `application/access_policy.json`, la source unique de la matrice d'accès. Ils ne peuvent
> donc pas décrire autre chose que ce que le serveur expose réellement.

---

## 1. Se connecter

Le transport de démonstration est **stdio** : l'hôte lance le serveur en sous-processus et le
profil est attaché au processus.

> 📖 **stdio** : le client et le serveur échangent par l'entrée et la sortie standard du
> processus, sans réseau. C'est le transport MCP local le plus simple à auditer.

```powershell
$env:SORABEL_PROFILE = "support"
uv run python -m mcp_server.server
```

Un processus = un profil = une session. **Le profil ne peut pas changer en cours de session** :
c'est ce qui permet de filtrer le catalogue lui-même, et pas seulement les appels.

Le client de démonstration fait les deux en une commande :

```powershell
uv run python scripts/mcp_client.py --profile support
uv run python scripts/mcp_client.py --profile commercial --tool ask_database --args '{"question":"combien de commandes en avril ?"}'
```

---

## 2. Les huit contrats

<!-- GENERE:catalogue-tools:debut — ne pas éditer à la main, voir scripts/generer_docs_matrice.py -->
> 🔒 Bloc **généré** depuis `application/access_policy.json`.
> Le modifier ici n'a aucun effet sur le code : modifier la politique, puis relancer
> `uv run python scripts/generer_docs_matrice.py`.

| Famille | Tool | Entrée | Sortie | Garantie | Profils |
|---|---|---|---|---|---|
| RAG | `answer_question` | `question` | réponse rédigée + liste des documents cités | citation obligatoire, sinon hors_corpus | support, commercial |
| RAG | `search_docs` | `query`, `limit` | passages classés avec doc_id, collection, score | recherche sans génération ; collections filtrées en amont | support, commercial, developer |
| RAG | `get_document` | `doc_id`, `version` | texte intégral + métadonnées | document autorisé au profil seulement | support, commercial, developer |
| RAG | `list_sources` | aucune | inventaire des documents du profil | catalogue filtré par profil | support, commercial, developer |
| SQL | `ask_database` | `question` | SQL + paramètres + colonnes + lignes + versions | lecture seule, requête validée, requête rendue vérifiable | support, commercial |
| SQL | `get_schema` | aucune | vues, colonnes, relations, KPI du profil | aucune donnée métier ; schéma physique jamais exposé | commercial, developer |
| SQL | `check_stock` | `reference` | SQL figée + lignes de stock par entrepôt | requête figée et paramétrée | support, commercial |
| SQL | `order_status` | `order_id` | SQL figée + statut de la commande | format vérifié ; requête figée et paramétrée | support, commercial |
<!-- GENERE:catalogue-tools:fin -->

---

## 3. Ce que votre agent reçoit dans `tools/list`

Un agent ne dispose de rien d'autre que ce texte pour choisir un tool. Il est reproduit ici
**mot pour mot** : c'est la chaîne exacte renvoyée par le serveur.

<!-- GENERE:descriptions-tools:debut — ne pas éditer à la main, voir scripts/generer_docs_matrice.py -->
> 🔒 Bloc **généré** depuis `application/access_policy.json`.
> Le modifier ici n'a aucun effet sur le code : modifier la politique, puis relancer
> `uv run python scripts/generer_docs_matrice.py`.

#### `answer_question` — Réponse sourcée à une question documentaire

```text
Répond à une question portant sur la documentation Sorabel — fiches techniques, notices, procédures SAV — et cite les documents utilisés.
Utiliser quand l'utilisateur attend une réponse rédigée. Ne pas utiliser pour inspecter les passages bruts : search_docs est fait pour cela.
Renvoie status=ok avec la réponse et ses sources, ou status=hors_corpus si aucun document autorisé ne permet de répondre : ce tool n'invente jamais de réponse. Seules les collections du profil sont interrogées.
```

#### `search_docs` — Recherche de passages, sans génération

```text
Recherche les passages documentaires les plus pertinents pour une requête, par recherche hybride — dense et BM25 fusionnés.
Utiliser pour inspecter la matière brute, vérifier ce que le corpus contient, ou enchaîner ensuite sur get_document. Ne pas utiliser quand une réponse rédigée est attendue.
Renvoie les passages classés avec leur doc_id, leur collection et leur score. Les collections interdites au profil sont filtrées avant le classement, jamais après.
```

#### `get_document` — Lecture d'un document complet

```text
Renvoie le texte intégral d'un document et ses métadonnées : référence, version, date, type.
Utiliser après search_docs, avec le doc_id qu'il a renvoyé, quand le passage ne suffit pas. Ne pas utiliser pour chercher : ce tool exige un identifiant connu.
Un document appartenant à une collection interdite au profil est refusé, même si son doc_id est connu.
```

#### `list_sources` — Inventaire des documents visibles

```text
Liste les documents que le profil a le droit de consulter : titre, référence, version, date, type.
Utiliser pour savoir ce que le corpus contient avant de chercher, ou pour vérifier la couverture documentaire. Ne pas utiliser pour lire un contenu : get_document est fait pour cela.
La liste est déjà filtrée par profil : ce qui n'y figure pas n'est pas accessible.
```

#### `ask_database` — Question métier libre sur la base de données

```text
Traduit une question en français en requête SQL de lecture, l'exécute, et renvoie le résultat AVEC la requête produite et ses paramètres.
Utiliser pour toute analyse variable : comptages, totaux, moyennes, classements, filtres par période. Ne pas utiliser pour le stock d'une référence précise — check_stock — ni pour une commande précise — order_status : ces deux-là sont plus rapides et plus prévisibles.
Aucune écriture ne passe : la requête est validée par arbre syntaxique puis exécutée en transaction READ ONLY. Une demande d'écriture renvoie UNSAFE_SQL, une colonne interdite au profil NOT_AUTHORIZED, une donnée absente du schéma OUT_OF_SCHEMA, une question imprécise AMBIGUOUS_QUESTION.
```

#### `get_schema` — Schéma sémantique visible par le profil

```text
Renvoie les vues, colonnes, relations et indicateurs que le profil a le droit d'interroger, avec leur description métier.
Utiliser pour construire une question juste avant d'appeler ask_database, ou pour intégrer la gateway dans un outil. Ne pas utiliser pour obtenir des données : ce tool ne renvoie que le schéma.
N'exécute aucune requête. Le schéma physique brut n'est jamais exposé : seul le catalogue sémantique du profil l'est.
```

#### `check_stock` — Stock d'une référence produit

```text
Renvoie le stock d'une référence produit, entrepôt par entrepôt, par une requête écrite d'avance et paramétrée.
Utiliser pour une référence précise au format REF-NNNN. Ne pas utiliser pour un total, un cumul ou une comparaison entre produits : ce tool renvoie le détail, pas une somme — passer par ask_database.
La requête est figée : seul le paramètre de référence varie, sa surface d'erreur est nulle.
```

#### `order_status` — Statut d'une commande

```text
Renvoie le statut et les éléments d'une commande identifiée, par une requête écrite d'avance et paramétrée.
Utiliser avec un identifiant au format CMD-AAAA-NNNN, dont le format est vérifié avant exécution. Ne pas utiliser pour chercher des commandes selon un critère : passer par ask_database.
Renvoie NOT_FOUND si la commande n'existe pas — ce qui est un résultat, pas une erreur.
```

<!-- GENERE:descriptions-tools:fin -->

---

## 4. Qui a le droit d'appeler quoi

<!-- GENERE:matrice-tools:debut — ne pas éditer à la main, voir scripts/generer_docs_matrice.py -->
> 🔒 Bloc **généré** depuis `application/access_policy.json`.
> Le modifier ici n'a aucun effet sur le code : modifier la politique, puis relancer
> `uv run python scripts/generer_docs_matrice.py`.

| Profil | `answer_question` | `search_docs` | `get_document` | `list_sources` | `ask_database` | `get_schema` | `check_stock` | `order_status` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Support client | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | DENY | ALLOW | ALLOW |
| Commercial | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| Développeur / IDE | DENY | ALLOW | ALLOW | ALLOW | DENY | ALLOW | DENY | DENY |
<!-- GENERE:matrice-tools:fin -->

### Périmètre documentaire

<!-- GENERE:matrice-collections:debut — ne pas éditer à la main, voir scripts/generer_docs_matrice.py -->
> 🔒 Bloc **généré** depuis `application/access_policy.json`.
> Le modifier ici n'a aucun effet sur le code : modifier la politique, puis relancer
> `uv run python scripts/generer_docs_matrice.py`.

| Collection | Support client | Commercial | Développeur / IDE |
|---|:---:|:---:|:---:|
| `fiches_techniques` — Fiches techniques produit | ALLOW | ALLOW | ALLOW |
| `notices` — Notices d'utilisation | ALLOW | ALLOW | ALLOW |
| `procedures_sav` — Procédures SAV | ALLOW | ALLOW | ALLOW |
| `notes_internes` — Notes internes — commerciales et tarifaires | DENY | ALLOW | ALLOW |
<!-- GENERE:matrice-collections:fin -->

### Périmètre SQL

L'axe *colonnes* n'est pas répété ici : il est porté par `sql/semantic_catalog.json`, où chaque
vue déclare les profils qui la voient. `get_schema` renvoie à votre client exactement le
périmètre de son profil — c'est la façon recommandée de le découvrir depuis le code.

Concrètement, pour le profil `support`, les colonnes `prix_achat_ht`, `marge_pct` et `marge_ht`
**n'existent pas** dans le schéma qui lui est remis. Ce n'est pas un filtre appliqué après coup :
c'est une absence construite en amont.

---

## 5. Deux barrières, pas une

| Étape | Ce qui se passe | Ce que votre client doit en conclure |
|---|---|---|
| `tools/list` | le catalogue **annoncé** ne contient que les tools du profil | ne proposez à l'agent que ce qui est listé |
| `tools/call` | la matrice est **réappliquée** à chaque appel | un tool absent du catalogue reste refusé proprement, pas par une erreur de protocole |

Cacher un tool ne suffit pas : un client qui appelle quand même reçoit une enveloppe typée et
l'appel est journalisé. C'est volontaire — un catalogue filtré est une commodité, la matrice
est la sécurité.

---

## 6. Le contrat de réponse

Toute réponse est une enveloppe JSON :

```json
{"status": "ok", "payload": {}, "message": ""}
```

| `status` | Sens |
|---|---|
| `ok` | l'appel a abouti ; `payload` porte le résultat |
| `refused` | le profil, la question ou le SQL ne passent pas la politique |
| `clarification` | la question est recevable mais imprécise |
| `hors_corpus` | aucun document autorisé ne permet de répondre |
| `execution_error` | incident technique contrôlé ; `message` porte le `request_id` |

Un refus porte en outre un **code d'erreur** dans `payload.error_code` :

| Code | Sens | Ce que le client doit faire |
|---|---|---|
| `NOT_AUTHORIZED` | tool, table ou colonne interdits au profil | afficher un refus neutre ; ne pas réessayer |
| `UNSAFE_SQL` | la demande implique une écriture | ne rien exécuter |
| `OUT_OF_SCHEMA` | la donnée n'existe pas dans le schéma visible | expliquer la limite |
| `UNSUPPORTED_QUESTION` | la donnée existe mais le générateur ne sait pas la traduire | proposer de reformuler |
| `AMBIGUOUS_QUESTION` | critère métier manquant | demander la précision indiquée |
| `NOT_FOUND` | requête correcte, aucune ligne | signaler l'absence |

> ⚠️ **Une erreur n'est jamais une donnée métier.** Ne la repassez pas au modèle comme si
> c'était un résultat : il la reformulerait en réponse plausible et fausse.

---

## 7. Le journal

Chaque appel — **autorisé comme refusé** — écrit une ligne JSON dans `logs/journal.jsonl` :

```powershell
$env:GATEWAY_JOURNAL = "logs/ma-session.jsonl"
```

| Champ | Contenu |
|---|---|
| `request_id` | identifiant unique de l'appel |
| `channel` | `mcp` ou `web` |
| `profile`, `tool`, `status`, `error_code` | la décision |
| `question`, `sql` | la demande et la requête produite, tronquées à 500 caractères |
| `row_count`, `duration_ms` | volume et temps |
| 4 champs de version | `dataset_version`, `data_as_of`, `semantic_schema_version`, `policy_version` |

Ne sont **jamais** journalisés : mot de passe, DSN, clé d'API, jeton.

---

## 8. Limites annoncées

1. **L'identité n'est pas industrialisée.** Le profil vient de `SORABEL_PROFILE`. En production
   il viendrait d'un jeton OIDC — Keycloak est documenté dans le dossier de conception, il n'est
   pas branché.
2. **Un profil par processus.** Le filtrage de `tools/list` repose là-dessus. Un transport
   réseau multi-sessions demanderait de porter le profil dans la session MCP.
3. **`answer_question` est extractif**, pas génératif : il choisit la meilleure phrase du corpus
   plutôt que d'en rédiger une. La recherche hybride, elle, est réelle et mesurée.

---

## 📖 Glossaire

| Terme | Définition |
|---|---|
| **MCP** | *Model Context Protocol* — protocole standard d'exposition de tools à un agent. |
| **Tool** | Fonction exposée par le serveur, avec un nom, un schéma d'entrée et une description. |
| **`tools/list`** | Appel du protocole qui demande le catalogue des tools disponibles. |
| **`tools/call`** | Appel du protocole qui exécute un tool avec ses arguments. |
| **stdio** | Transport local : échanges par entrée/sortie standard, sans réseau. |
| **Profil** | Rôle métier qui détermine les droits : `support`, `commercial`, `developer`. |
| **Matrice d'accès** | Tableau des droits profil × ressource. |
| **Enforcement** | Le flux qui applique ces droits, à chaque frontière. |
| **Enveloppe** | Le format commun de toute réponse : `{status, payload, message}`. |
| **Journal d'audit** | Trace de chaque appel : qui, quoi, quand, quelle décision. |
