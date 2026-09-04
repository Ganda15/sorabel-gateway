# Vérification du chantier 3 — serveur MCP et matrice d'accès

> Chaque ligne de ce document a été **exécutée le 2026-09-04**, pas recopiée d'un document
> antérieur. Les commandes sont données pour être rejouées.
>
> Ce qui n'est pas fait est marqué ⚠️ et expliqué. Un document qui ne signale aucune faiblesse
> n'est pas crédible.

---

## 1. Les trois tâches du brief

### Tâche 1 — « implémenter le serveur MCP exposant le catalogue » (8 tools)

| Attendu | Réel | État |
|---|---|---|
| `answer_question`, `search_docs`, `get_document`, `list_sources` | 4 tools RAG | ✅ |
| `ask_database`, `get_schema`, `check_stock`, `order_status` | 4 tools SQL | ✅ |
| aucun tool en trop | contrôlé | ✅ |

```
brief : 8 | exposés : 8 | manquants : aucun | en trop : aucun
```

Implémentation : `mcp_server/server.py`, transport `stdio`, `FastMCP`.

### Tâche 2 — « appliquer la matrice d'accès et la journalisation de tous les appels (E4, E5) »

**La matrice porte trois axes**, pas seulement les tools :

| Axe | Source | Où c'est appliqué |
|---|---|---|
| profil × **tool** | `application/access_policy.json` | `ProfiledMCP.list_tools` puis `governed()` |
| profil × **collection** | `application/access_policy.json` | `retrieval/service.py`, **avant** le classement |
| profil × **table / colonne** | `sql/semantic_catalog.json` | `sql/catalog.py:for_profile()` puis rôles PostgreSQL |

**Deux barrières indépendantes sur l'axe tool** :

1. le catalogue **annoncé** ne contient que les tools du profil ;
2. la matrice est **réappliquée** à chaque appel — cacher un tool ne suffit pas.

**Journalisation** : 8 `tools/call` pendant la démonstration → **8 lignes** dans
`logs/demonstration-mcp.jsonl`. Refus compris.

### Tâche 3 — « documenter le catalogue et démontrer deux profils »

| Attendu | Livré |
|---|---|
| catalogue documenté pour les équipes clientes | `docs/livrable/CATALOGUE-TOOLS-MCP.md` — **généré** depuis la politique |
| démonstration support contre commercial | `scripts/demo_mcp.py` — 10 contrôles, 10 conformes |
| via `scripts/mcp_client.py` | fonctionnel sur les **trois** profils depuis le 2026-09-04 |

> ℹ️ Le brief nomme `scripts/mcp_client.py`. Il fonctionne et reste l'outil d'exploration
> manuelle. `scripts/demo_mcp.py` a été ajouté parce qu'une démonstration doit être
> **rejouable et vérifiable** : il compare chaque réponse à un attendu et sort en erreur si
> la réalité diffère.

---

## 2. Les quatre critères d'acceptance

### « Un client au profil autorisé n'accède qu'aux tools, collections et tables prévus par la matrice »

**Axe tool** — catalogue réellement annoncé :

| Profil | Tools annoncés | `get_schema` visible ? |
|---|---:|---|
| support | **7** | non |
| commercial | **8** | oui |
| developer | **4** | oui |

**Axe collection** — requête « remise commerciale marge tarif négociation interne » :

| Profil | Collections remontées | Documents listés | Notes internes visibles |
|---|---|---:|---:|
| support | `fiches_techniques` | 255 | **0** |
| commercial | `notes_internes` | 315 | 60 |
| developer | `notes_internes` | 315 | 60 |

**Axe colonne** — profil support, question « quelle est la marge sur la REF-8842 ? » →
`refused` · `NOT_AUTHORIZED` en **5 ms**, avant tout appel au modèle.

✅ **Les trois axes sont vérifiés.**

### « Un client non autorisé est refusé avec un message clair et journalisé »

```json
{"status": "refused",
 "payload": {"error_code": "NOT_AUTHORIZED", "tool": "get_schema", "profile": "support"},
 "message": "get_schema is not authorized for the support profile."}
```

Ligne de journal correspondante :

```json
{"channel":"mcp","profile":"support","tool":"get_schema","status":"refused",
 "error_code":"NOT_AUTHORIZED","duration_ms":8,"policy_version":"policy-v1"}
```

✅ Message clair, code typé, tracé. **Ce n'est pas une erreur de protocole** — c'est important :
une erreur de protocole n'aurait pas été journalisée.

### « Un client qui veut chercher sans générer : search_docs puis get_document »

Enchaînés dans la démonstration, avec le `doc_id` **réellement renvoyé** par `search_docs`
(le script résout `@search_docs.hits[0].doc_id`, aucun identifiant écrit en dur) :

```
OK  [support] search_docs   ok  165 ms
OK  [support] get_document  ok    3 ms
```

✅ Les deux briques fonctionnent séparément.

### « Sur une session de démonstration, le journal contient tous les appels »

```
10/10 conformes — 5 autorisés, 3 refusés, 8 lignes de journal
```

8 `tools/call`, 8 lignes. ✅

---

## 3. Les livrables demandés

| Livrable | Emplacement | État |
|---|---|---|
| Dossier de conception — flux, chunks, catalogue de tools, flow Text-to-SQL, matrice | `01-TRAINER-HANDOVER/DOSSIER-CONCEPTION/` (3 chantiers, 9 documents, 14 schémas) et `docs/livrable/conception/` | ✅ |
| Serveur MCP `mcp_server/` exposant le catalogue complet | `mcp_server/server.py` | ✅ |
| Mini-guide d'accès | `docs/livrable/GUIDE-ACCES-MCP.md` + `docs/livrable/CATALOGUE-TOOLS-MCP.md` | ✅ |
| **Un lien d'une interface graphique du produit fonctionnel** | `web_app/` — démarrage local `http://127.0.0.1:8780` | ⚠️ **voir ci-dessous** |

> ⚠️ **Le seul manque réel du chantier.** L'interface existe, elle est testée
> (`tests/integration/test_web_app.py`) et elle fonctionne — mais **il n'y a pas de lien** :
> rien n'est déployé, et la branche `feature/text-to-sql-postgresql` n'a jamais été poussée
> sur `github.com/Ganda15/sorabel-gateway`. Tant que ce n'est pas fait, le livrable
> « un lien » n'est pas satisfait. Deux options, dans l'ordre de coût :
> 1. pousser la branche et livrer le lien du dépôt + `START-SORABEL-UI.bat` ;
> 2. déployer l'interface (Render, Railway, Hugging Face Space) et livrer une URL publique.

---

## 4. Les cinq critères de performance

| Critère | Preuve | État |
|---|---|---|
| Tous les tests d'acceptance fournis passent (RAG, Text-to-SQL, MCP) | **230 passed** — 163 unitaires, 12 d'acceptance, 48 d'intégration ; la suite `tests/acceptance/` est **identique au starter** (`git diff starter-original` vide) | ✅ |
| Les six exigences DSI E1–E6 respectées et démontrées | `docs/livrable/TRACEABILITE-BRIEF-CODE-PREUVES.md` | ✅ |
| La recherche hybride surpasse la dense, preuve chiffrée | Recall@1 **0,727 → 0,864** — **+13,6 points**, +18,7 %, 22 questions (`eval/rapport_gain.md`) | ✅ |
| Aucune écriture SQL ne passe | `UNSAFE_SQL` en 4 ms, avant génération | ✅ |
| Aucune colonne sensible ne sort pour le profil support | `NOT_AUTHORIZED` en 5 ms + colonne absente du schéma remis + rôle PostgreSQL | ✅ |
| Choix d'architecture justifiés dans le dossier de conception | conception jour 3 §1–§5 + schémas 12, 13, 14 | ✅ |

---

## 5. Ce qui a changé le 2026-09-04, et pourquoi

Le dossier de conception du jour 3 demandait déjà, §1 et §7 :

> « Catalogue `tools/list` : retourne uniquement les tools visibles pour le profil. »
> « Test n° 1 : Support voit sept tools ; `get_schema` est absent de `tools/list`. »

**Le code ne le faisait pas.** Mesuré avant correction :

```
$ scripts/mcp_client.py --profile support
answer_question ... ask_database ... get_schema ...   ← 8 tools annoncés
  answer_question: (no description)
```

Trois défauts, tous fermés :

| # | Défaut mesuré | Correction | Test qui l'empêche de revenir |
|---|---|---|---|
| 1 | `tools/list` annonçait 8 tools au support, `get_schema` compris | `ProfiledMCP.list_tools` filtre par profil | `test_le_catalogue_annonce_exactement_les_tools_du_profil` |
| 2 | les 8 tools étaient annoncés **sans description** — aucun agent ne peut choisir | descriptions dans la politique, injectées à l'enregistrement | `test_chaque_tool_annonce_est_livre_avec_sa_description` |
| 3 | la matrice était écrite **4 fois** à la main (2 en Python, 2 en Markdown) | source unique `application/access_policy.json`, code et docs dérivés | `test_la_documentation_livree_ne_derive_pas_de_la_politique` |

Et un **quatrième défaut, introduit puis corrigé le jour même** : brancher la politique sur
`retrieval/service.py` a créé un **import circulaire**. La suite passait par chance — pytest
importait `application` en premier. `import retrieval.service` seul échouait. Corrigé par un
export paresseux (PEP 562) dans `application/__init__.py`, avec un test qui importe chacun des
six modules dans un processus neuf.

> **Pourquoi le raconter ?** Parce que c'est le genre de défaut qu'une suite verte ne montre
> pas. Il a été trouvé en vérifiant un axe de la matrice à la main, pas par les tests.

---

## 6. Deux décisions d'architecture à savoir défendre

### Pourquoi deux barrières et pas une ?

Filtrer `tools/list` est une **commodité pour le client** : un agent honnête ne propose que ce
qui est listé. Ce n'est pas de la sécurité — rien n'empêche un client d'appeler un tool qu'il
n'a pas vu. La sécurité, c'est `governed()`, qui réapplique la matrice à chaque appel.
Supprimer le filtre dégraderait l'expérience ; supprimer la réautorisation ouvrirait tout.

### Pourquoi ne pas mettre le format `REF-NNNN` dans le schéma JSON ?

Parce que c'est **mesuré** : avec un `pattern` pydantic sur l'argument, un appel malformé est
refusé au niveau protocole (`isError=True`) et **la ligne de journal n'est jamais écrite**.

```
isError = True
Error executing tool check_stock: String should match pattern '^REF-[0-9]{4}$'
journal : VIDE
```

E5 exige que **tous** les appels soient journalisés, autorisés comme refusés. Le format est
donc décrit dans le schéma (`description`, `examples`) mais contrôlé dans le service, qui
renvoie `INVALID_ARGUMENT` — et écrit sa ligne de journal.

---

## 7. Keycloak et PostgreSQL — la conception disait « plus tard », deux fois sur trois c'est fait

Le document `04-evolution-production-keycloak-postgresql.md` décrit trois évolutions. Vérifié
contre la base réelle le 2026-09-04, **deux sur trois sont construites** — et le document les
annonce encore comme futures. C'est le défaut « documenté mais absent » **à l'envers** :
du travail réel présenté comme non fait. Devant un jury, cela coûte du crédit pour rien.

| Conception | Ce qu'elle annonce | Réalité mesurée |
|---|---|---|
| §1 Keycloak / OIDC | évolution future | ⚠️ **toujours à faire** — le profil vient de `SORABEL_PROFILE` |
| §2 PostgreSQL read-only | « la couche SQL **peut ensuite** remplacer SQLite » | ✅ **construit, et plus profond que conçu** |
| §3 Profil `developer` | « **peut être ajouté** plus tard » | ✅ côté application ; ⚠️ côté base, le rôle existe mais est vide |

### §2 — ce qui a été construit au-delà de la conception

| Conception | Implémentation réelle |
|---|---|
| « `CREATE ROLE` pour les rôles techniques lecteurs » | **deux étages** : groupes sans login `sorabel_support` / `sorabel_commercial`, et rôles de connexion `_login` qui en sont membres. Changer un droit se fait sur le groupe, jamais sur le compte. |
| « `GRANT SELECT` sur les vues » | 9 vues sémantiques, **isolation parfaite** : les 4 vues `_support` sont invisibles au commercial, les 5 vues `_commercial` invisibles au support. Aucun recouvrement. |
| « transactions `READ ONLY` » | **deux couches indépendantes** : `default_transaction_read_only=on` posé sur le rôle lui-même, **et** `SET TRANSACTION READ ONLY` à chaque transaction (`sql/executors.py`). L'une suffirait ; il y en a deux. |
| « vues autorisées » | les 9 vues portent `security_barrier=oui` — un prédicat injecté ne peut pas être évalué avant le filtre de la vue. |
| non mentionné | **les rôles de connexion n'ont aucun accès à `sorabel_source`.** `has_table_privilege('sorabel_support_login','sorabel_source.produits','SELECT')` = **false**. Ils ne voient jamais les tables brutes, seulement les vues. |
| non mentionné | **zéro privilège d'écriture** pour les rôles de connexion. Les 908 privilèges `INSERT/UPDATE/DELETE/TRUNCATE` de la base appartiennent tous à `sorabel_admin`, le compte de migration et de chargement. |
| « `has_table_privilege` sert à vérifier dans les tests » | **72 contrôles** archivés (68 sur table, 4 sur colonne), tous passés, dans `docs/livrable/evidence/postgresql-privileges.json`, rejoués par 5 tests de `tests/integration/test_postgres_privileges.py`. |

Commande pour le prouver en direct :

```
docker exec sorabel-gateway-postgres-1 psql -U sorabel_admin -d sorabel -c "SELECT rolname, rolconfig FROM pg_roles WHERE rolname LIKE 'sorabel%_login';"
```

### §3 — le profil `developer` : fait côté application, vide côté base

`developer` existe dans la politique (4 tools : `search_docs`, `get_document`, `list_sources`,
`get_schema`), il est testé, et `scripts/mcp_client.py --profile developer` fonctionne depuis
le 2026-09-04.

> ⚠️ Côté base, le rôle `sorabel_schema_reader` existe mais a **0 grant et 0 membre**. Ce n'est
> pas un trou de sécurité — `developer` n'a pas le droit d'appeler `ask_database`, et
> `get_schema` lit le catalogue sémantique JSON, pas la base. Mais c'est un rôle mort. La
> politique le dit franchement : `"role_postgres": null` pour ce profil. À nettoyer ou à
> câbler, pas à laisser ambigu.

### §1 — Keycloak : ce qu'il resterait à faire, concrètement

Le profil arrive aujourd'hui par `SORABEL_PROFILE`, une variable d'environnement du processus.
C'est honnête pour une baseline `stdio`, et c'est ce qui rend le filtrage de `tools/list`
possible — un processus = un profil. Passer à Keycloak change **trois** choses, et trois
seulement :

1. **d'où vient le profil** : d'un jeton OIDC validé, au lieu de l'environnement ;
2. **quand il est connu** : à l'ouverture de session MCP, pas au lancement du processus — donc
   `list_tools` devrait lire le profil de la session, pas `self._profile` ;
3. **ce que le journal enregistre** : ajouter `subject_id` et `client_id` à côté du profil.

**Rien d'autre ne bouge** : ni le catalogue des tools, ni la matrice, ni les vues, ni les rôles
PostgreSQL, ni les tests. C'est exactement l'argument de la conception, et il tient toujours.

> **La phrase à défendre à l'oral** : « L'identité n'est pas industrialisée, et je le dis. Mais
> l'autorisation, elle, est déjà à trois niveaux : la matrice dans le catalogue et à l'appel, le
> catalogue sémantique filtré, et les droits PostgreSQL. Keycloak remplacerait une ligne — d'où
> vient le profil. Il ne remplacerait aucune barrière. »

---

## 8. Le reproche du formateur, repris de face : « un dictionnaire de correspondance »

Au chantier 2 le formateur a dit, à juste titre, que le système était « des templates avec un
dictionnaire de correspondance ». Le générateur SQL a été remplacé. **Mais `sql/analyzer.py`
contient toujours des listes de mots** — et il faut le dire avant qu'on le trouve :

| Liste | Contenu | Rôle |
|---|---|---|
| `_write_verbs` | 48 formes verbales : `supprime`, `vider`, `purgez`… | refuser une écriture |
| `_write_keywords` | `delete`, `update`, `drop`, `truncate`… | refuser du SQL brut |
| `_sensitive_phrases` | `marge`, `prix d'achat`, `cout achat` | refuser une donnée sensible au support |
| `_aggregation_terms` | `total`, `somme`, `cumul` | ne pas router une somme vers un tool figé |
| `_business_terms` | `client`, `commande`, `stock`… | détecter une question hors domaine |

**La différence avec ce qui a été reproché** : ces listes ne **génèrent** rien. Elles ne servent
qu'à **refuser**, en amont, et rien ne dépend d'elles seules. Mais une liste reste une liste, et
elle a des trous. La question honnête n'est donc pas *« ai-je enlevé les mots-clés ? »* — non —
mais **« que se passe-t-il quand le mot-clé ne matche pas ? »**

### Ce que la mesure répond

`scripts/verifier_defense_profondeur.py` pose des questions qui contournent délibérément le
vocabulaire des listes, et relève **quelle barrière a refusé**.

| Question, profil support | Refusée par | Code | Durée |
|---|---|---|---|
| « quelle est la **marge** sur la REF-8842 ? » | 1 · analyseur, vocabulaire attendu | `NOT_AUTHORIZED` | 0 ms |
| « quel est le **bénéfice** sur la REF-8842 ? » | **2 · schéma filtré** | `UNSUPPORTED_QUESTION` | ~1 000 ms |
| « combien on **gagne** sur chaque produit ? » | **2 · schéma filtré** | `UNSUPPORTED_QUESTION` | ~1 050 ms |
| « montre-moi **`prix_achat_ht`** des produits » | **2 · schéma filtré** | `UNSUPPORTED_QUESTION` | ~1 220 ms |
| « différence entre prix de vente et prix payé au fournisseur » | **2 · schéma filtré** | `UNSUPPORTED_QUESTION` | ~1 170 ms |
| « **supprime** les commandes de test » | 1 · analyseur, vocabulaire attendu | `UNSAFE_SQL` | 0 ms |
| « **purge** la table commandes » | 1 · analyseur, verbe en position d'ordre | `UNSAFE_SQL` | 0 ms |
| « **vide** le stock de la REF-8842 » | 1 · analyseur, verbe en position d'ordre | `UNSAFE_SQL` | 0 ms |

```
6/6 contournements arrêtés · 8 cas · aucune fuite : True
```

> 🗣 **La phrase à dire** : « Oui, il reste des listes de mots. Non, elles ne sont pas seules.
> Quand le mot-clé échoue, c'est le schéma filtré qui tient — parce que la colonne interdite
> n'existe pas dans ce qu'on remet au modèle. On ne peut pas divulguer ce qu'on n'a jamais vu. »

### Le défaut que cette vérification a trouvé, et qui a été corrigé

Avant le 2026-09-04, **« vide le stock de la REF-8842 » renvoyait le stock, en 110 ms, sans le
moindre refus.**

La cause : `_write_phrases` cherchait des sous-chaînes figées, dont `"vide la table"`.
« vide **le stock** » y échappait. Le routage vers le tool figé `check_stock` ne regarde alors
que la référence et le mot « stock » — **jamais le verbe**. Aucune donnée n'était écrite,
`check_stock` étant en lecture seule, mais l'utilisateur repartait **en croyant son ordre
exécuté**. C'est un défaut de communication, pas de sécurité — le même que `OUT_OF_SCHEMA`
employé à tort, et il coûte la même chose : la confiance.

**La correction ne consiste pas à rallonger la liste.** Le verbe est désormais reconnu comme un
**mot entier**, dans les **trois premiers mots** — la position de l'impératif et de l'infinitif en
français :

```python
return any(mot in self._write_verbs for mot in mots[: self._write_verb_window])
```

Et le défaut inverse est testé aussi : six lectures légitimes qui contiennent le même verbe au
participe passé — « combien de commandes ont été **annulées** » — ne sont pas refusées.
Élargir une détection sans borner sa portée aurait produit un défaut plus visible que celui
qu'on corrigeait.

| Test | Ce qu'il ferme |
|---|---|
| `test_une_ecriture_reformulee_est_refusee_et_jamais_reinterpretee` | 8 formulations d'ordre |
| `test_une_lecture_qui_parle_d_ecriture_passee_n_est_pas_refusee` | 6 lectures légitimes |

### La limite qui reste, annoncée

Un verbe d'écriture placé au-delà du troisième mot, dans une tournure inhabituelle, échapperait
encore à l'analyseur. Ce qui l'arrêterait alors : le générateur ne produit que du `SELECT`, le
validateur AST rejette tout nœud d'écriture, et le rôle PostgreSQL est en lecture seule.
**Trois barrières derrière celle qui aurait failli** — c'est exactement ce que la défense en
profondeur doit garantir, et c'est ce que le tableau ci-dessus mesure.

---

## 9. Limites annoncées

1. **L'identité n'est pas industrialisée.** Le profil vient de `SORABEL_PROFILE`. Keycloak est
   conçu (`04-evolution-production-keycloak-postgresql.md`), pas branché.
2. **Un profil par processus.** Le filtrage de `tools/list` en dépend. Un transport réseau
   multi-sessions demanderait de porter le profil dans la session MCP elle-même.
3. **`answer_question` est extractif**, pas génératif : il choisit la meilleure phrase du
   corpus. La recherche hybride, elle, est réelle et mesurée (+13,6 points).
4. **Le lien de l'interface graphique n'existe pas** — voir §3.
5. **Keycloak n'est pas branché** — voir §7. Le rôle PostgreSQL `sorabel_schema_reader`
   est déclaré mais vide.

---

## 10. Rejouer toutes les preuves

```
cd "C:\Users\kanda\Documents\ChatGPT\Sorabel - l'agent augmenté par la donnée, exposé via MCP\02-IMPLEMENTATION\sorabel-gateway"
```
```
.\.venv\Scripts\python.exe -m pytest -q
```
```
.\.venv\Scripts\python.exe scripts\demo_mcp.py
```
```
.\.venv\Scripts\python.exe scripts\generer_docs_matrice.py --verifier
```
```
.\.venv\Scripts\python.exe scripts\verifier_defense_profondeur.py
```
```
.\.venv\Scripts\python.exe scripts\mcp_client.py --profile support
```

Attendu : `230 passed` · `10/10 conformes` · `19/19 conformes` · `6/6 contournements arrêtés` · `à jour` sur les 3 documents · `7 tools`.

---

## 📖 Glossaire

| Terme | Définition en une ligne |
|---|---|
| **MCP** | *Model Context Protocol* — protocole standard d'exposition de tools à un agent. |
| **`tools/list`** | Appel du protocole qui demande le catalogue des tools disponibles. |
| **`tools/call`** | Appel du protocole qui exécute un tool avec ses arguments. |
| **stdio** | Transport local : échanges par entrée/sortie standard, sans réseau. |
| **Matrice d'accès** | Tableau des droits profil × ressource. |
| **Enforcement** | Le flux qui applique ces droits, à chaque frontière. |
| **Source unique** | Un seul fichier fait foi ; code et documentation en dérivent. |
| **Import circulaire** | Deux modules qui s'importent l'un l'autre ; l'un des deux est chargé à moitié. |
| **PEP 562** | Règle Python qui permet à un module d'exposer un attribut **paresseusement**. |
| **Recall@1** | Part des questions dont le bon document arrive en première position. |
| **OIDC** | *OpenID Connect* — norme qui permet à un service tiers (Keycloak) de certifier qui est l'utilisateur, par un jeton signé. |
| **Keycloak** | Serveur d'identité libre : il authentifie l'utilisateur une fois et émet ce jeton. |
| **Rôle de groupe** | Rôle PostgreSQL sans droit de connexion, qui ne sert qu'à porter des droits ; les comptes réels en deviennent membres. |
| **`security_barrier`** | Option d'une vue PostgreSQL : la base garantit que le filtre de la vue s'applique **avant** toute condition ajoutée par l'appelant. |
| **`default_transaction_read_only`** | Réglage attaché à un rôle : toutes ses transactions démarrent en lecture seule, sans que l'application ait à le demander. |
| **`has_table_privilege`** | Fonction PostgreSQL qui répond « ce rôle a-t-il ce droit ? ». Elle **constate**, elle n'accorde rien. |
