# Mettre la gateway en ligne

Cinq conteneurs sur le serveur : **l'app** (interface web, serveur MCP lancé en
sous-processus, scripts de mise en place), **PostgreSQL** (les cinq barrières Text-to-SQL
restent intactes), et **trois serveurs MCP joignables à distance**, un par profil, en
`streamable-http`. Devant, le **Caddy déjà installé sur le serveur** ajoute un site : HTTPS
automatique, un mot de passe pour l'interface, un jeton par serveur MCP. Rien n'est
simulé : c'est le même code qu'en local, avec la même base.

Le résultat, pour le formateur :

- une adresse `https://…` où il teste les trois chantiers dans l'interface — RAG,
  Text-to-SQL, et le panneau MCP qui lance un vrai serveur à chaque clic ;
- trois adresses `https://…/mcp/<profil>` où il **branche son propre client MCP** —
  l'Inspector, un IDE, un `curl` — et voit le catalogue que le protocole annonce à ce
  profil. Le jeton qu'il présente **est** le profil : aucun formulaire ne le choisit.

## Ce qui a été vérifié avant d'écrire cette page

La pile complète a tourné sur un poste Windows, le 10 septembre 2026, avec les fichiers de
ce dossier tels quels :

| Chantier | Appel par l'API du conteneur | Résultat |
|---|---|---|
| 1 — RAG | procédure SAV, profil support | `ok`, 2 sources |
| 1 — RAG | télétravail, profil support | `hors_corpus` |
| 2 — SQL | commandes d'avril 2026, profil commercial | `ok`, backend **postgres**, `[[27]]`, SQL renvoyé |
| 2 — SQL | marge REF-8842, profil support | `refused` · `NOT_AUTHORIZED` |
| 2 — SQL | « supprime les commandes de test » | `refused` · `UNSAFE_SQL` |
| 3 — MCP | catalogue support · commercial · developer | **7 · 8 · 4** tools |
| 3 — MCP | support appelle `get_schema` | `refused` · `NOT_AUTHORIZED`, journalisé |
| 3 — MCP **à distance** | `tools/list` en JSON-RPC brut sur les trois serveurs HTTP | **7 · 8 · 4** tools, `get_schema` absent du support |
| 3 — MCP **à distance** | `tools/call` support → `get_schema` · commercial → `answer_question` | `refused` · `NOT_AUTHORIZED` / `ok`, source REF-8842 |

Suite de tests : **236 verts** — les 230 livrés, plus 6 sur le choix du transport.
Image : 1,13 Go, sans modèle à télécharger — l'embedder livré est un hachage local.

Le serveur visé, inventorié le même jour : Ubuntu, Docker 29 et Compose 2.40 présents,
4 Go de RAM, Caddy 2.11 en service système sur les ports 80 et 443, port 8780 libre.

## Les fichiers

| Fichier | Rôle |
|---|---|
| `../Dockerfile` | l'image de l'app : Python 3.11, dépendances par `uv`, sans l'extra `vector` |
| `../.dockerignore` | ce qui n'entre jamais dans l'image : `.env`, `.git`, tests, livrables |
| `demarrer.sh` | au démarrage : base SQLite, index, migrations + import PostgreSQL, puis `uvicorn` |
| `compose.prod.yml` | l'app, PostgreSQL et les trois serveurs MCP ; tous n'écoutent que sur `127.0.0.1` de l'hôte (8780, 8791–8793) |
| `caddy-site.conf` | le bloc à ajouter au Caddy du serveur : HTTPS, `basic_auth` pour l'interface, un jeton par serveur MCP |
| `.env.prod.example` | le modèle des variables ; `.env.prod` est ignoré par git |
| `Caddyfile` | variante « Caddy dans un conteneur » pour un serveur qui n'en a pas ; inactive ici |

## Procédure

Deux endroits, et il ne faut pas les confondre :

- 💻 **TON PC** — PowerShell local
- 🖧 **LE SERVEUR** — après `ssh root@178.104.184.125`

### 1 · Se connecter

💻 **TON PC**

```
ssh root@178.104.184.125
```

### 2 · Récupérer le code

🖧 **LE SERVEUR**

```
git clone -b livrable/sorabel-gateway https://github.com/Ganda15/sorabel-gateway.git /opt/sorabel
```

```
cd /opt/sorabel
```

### 3 · Écrire la configuration — jamais commitée

🖧 **LE SERVEUR**

```
cp deploy/.env.prod.example deploy/.env.prod
```

Trois mots de passe PostgreSQL, longs et distincts. Les générer plutôt que les inventer :

```
openssl rand -hex 24
```

Trois fois, et coller chaque valeur dans `deploy/.env.prod` :

```
nano deploy/.env.prod
```

| Variable | Valeur |
|---|---|
| `SORABEL_POSTGRES_PASSWORD` | premier `openssl rand` |
| `SORABEL_SUPPORT_PASSWORD` | deuxième |
| `SORABEL_COMMERCIAL_PASSWORD` | troisième |
| `SORABEL_SQL_GENERATOR` | `openai_compatible` pour gpt-5.4 comme en démo, `deterministic` sans clé |
| `SORABEL_SQL_LLM_*` | l'adresse, le modèle et la clé Azure — seulement si `openai_compatible` |

`SORABEL_HOTE` peut rester tel quel : il ne sert qu'à la variante « Caddy dans un conteneur ».

### 4 · Lancer l'app et sa base

🖧 **LE SERVEUR**

```
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml up -d --build
```

La première fois, la construction prend quelques minutes. Suivre le démarrage :

```
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml logs -f app
```

Les quatre étapes `[1/4]` à `[4/4]` doivent défiler, puis `Uvicorn running`. `Ctrl+C` quitte
le suivi sans arrêter les conteneurs. Contrôle depuis le serveur lui-même :

```
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8780/
```

Attendu : **200**. À ce stade, l'app n'est joignable que depuis le serveur — pas encore
depuis Internet.

### 5 · Le mot de passe du formateur, et les trois jetons MCP

Caddy ne stocke pas le mot de passe : il stocke son empreinte bcrypt. La produire :

🖧 **LE SERVEUR**

```
caddy hash-password --plaintext 'LE_MOT_DE_PASSE_CHOISI'
```

La sortie commence par `$2a$14$`. La coller à la place de `HASH_A_REMPLACER` dans
`deploy/caddy-site.conf`. Puis trois jetons, un par profil, générés plutôt qu'inventés :

```
openssl rand -hex 24
```

Trois fois ; coller chacun à la place de `JETON_SUPPORT`, `JETON_COMMERCIAL` et
`JETON_DEVELOPER` :

```
nano deploy/caddy-site.conf
```

Garder les trois jetons dans un fichier lisible par root seul : ce sont eux qu'on
transmettra au formateur, jamais par le même canal que le lien.

### 6 · Ajouter le site au Caddy du serveur

🖧 **LE SERVEUR**

```
cat deploy/caddy-site.conf >> /etc/caddy/Caddyfile
```

```
caddy validate --config /etc/caddy/Caddyfile
```

Attendu : `Valid configuration`. Si Caddy signale une erreur, ne pas recharger : ouvrir
`/etc/caddy/Caddyfile` avec `nano` et corriger d'abord.

```
systemctl reload caddy
```

Caddy demande alors un certificat à Let's Encrypt pour `sorabel.178-104-184-125.sslip.io`.
Cela prend de quelques secondes à une minute.

### 7 · Vérifier — ne pas s'en passer

💻 **TON PC**

```
curl -sS -o /dev/null -w "%{http_code}\n" https://sorabel.178-104-184-125.sslip.io/
```

Attendu : **401**. C'est le bon résultat — la page existe, elle demande le mot de passe.

```
curl -sS -o /dev/null -w "%{http_code}\n" -u formateur:LE_MOT_DE_PASSE_CHOISI https://sorabel.178-104-184-125.sslip.io/
```

Attendu : **200**. Puis ouvrir l'adresse dans un navigateur, entrer l'identifiant, et
rejouer la question « quelle est la marge sur la REF-8842 ? » en profil support puis
commercial.

### 8 · Transmettre au formateur

Le lien, l'identifiant `formateur` et le mot de passe — **par un canal séparé du message
qui donne le lien**. Le dépôt GitHub ne contient ni l'un ni l'autre.

## Brancher son propre client MCP à distance

Trois adresses, une par profil. Le jeton présenté décide du serveur atteint :

| Adresse | Jeton | Catalogue annoncé |
|---|---|---|
| `https://sorabel.178-104-184-125.sslip.io/mcp/support` | `JETON_SUPPORT` | 7 tools, sans `get_schema` |
| `https://sorabel.178-104-184-125.sslip.io/mcp/commercial` | `JETON_COMMERCIAL` | 8 tools |
| `https://sorabel.178-104-184-125.sslip.io/mcp/developer` | `JETON_DEVELOPER` | 4 tools, sans outil métier |

**Avec le MCP Inspector**, le client de référence du protocole :

```
npx -y @modelcontextprotocol/inspector
```

Dans la page qui s'ouvre : *Transport Type* → **Streamable HTTP** ; *URL* → l'adresse du
profil ; *Authentication* → **Bearer Token** → coller le jeton ; **Connect**. L'onglet
*Tools* montre alors le catalogue de ce profil, et le panneau *Protocol* les échanges
`initialize` / `tools/list` / `tools/call` chronométrés.

**Avec `curl`**, sans rien installer — le serveur est sans état, une requête se suffit :

```
curl -sS -H "Authorization: Bearer JETON_COMMERCIAL" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' https://sorabel.178-104-184-125.sslip.io/mcp/commercial
```

Sans jeton, ou avec le jeton d'un autre profil : **401**, et rien d'autre.

## Mettre à jour après un changement de code

🖧 **LE SERVEUR**

```
cd /opt/sorabel
```

```
git pull
```

```
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml up -d --build
```

Les données PostgreSQL et le journal sont dans des volumes : ils survivent à la
reconstruction. Le script de démarrage rejoue les migrations et l'import, tous deux
rejouables sans dommage. Caddy n'a pas à être touché.

## Couper l'accès quand le formateur a fini

Le déploiement est fait pour être **temporaire**. Trois niveaux, du plus doux au plus
radical.

🖧 **LE SERVEUR**

```
cd /opt/sorabel
```

| Niveau | Commande | Effet |
|---|---|---|
| **1 · Fermer la porte** | `docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml stop app mcp-support mcp-commercial mcp-developer` | le site et les serveurs MCP répondent **502** ; la base reste en place. `start` sur les mêmes rouvre en dix secondes |
| **2 · Tout éteindre** | `docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml down` | les cinq conteneurs s'arrêtent ; base et journal conservés dans leurs volumes |
| **3 · Tout effacer** | `docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml down -v` | plus rien ne reste, sauf le code cloné |

Après le niveau 3, retirer aussi le bloc `sorabel.…` de `/etc/caddy/Caddyfile` avec `nano`,
puis `systemctl reload caddy` — sinon Caddy continue de renouveler un certificat pour rien.
Et **révoquer la clé Azure** dans le portail si elle avait été mise dans `deploy/.env.prod` :
un secret qui a vécu sur un serveur se remplace.

Vérifier depuis le PC que la porte est bien fermée :

💻 **TON PC**

```
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 10 https://sorabel.178-104-184-125.sslip.io/
```

Attendu après le niveau 1 : **502**. Après le retrait du bloc Caddy : **000** ou une erreur
de certificat — le site n'existe plus.

## Ce que ce déploiement ne fait pas

- **Pas de fournisseur d'identité.** Dans l'interface web, le profil se choisit dans un
  menu, comme en local. Sur les serveurs MCP, c'est le jeton qui vaut identité : un
  secret partagé par profil, pas un compte par personne. Brancher Keycloak reste la
  limite documentée du projet.
- **Un serveur par profil.** Le filtrage du catalogue est attaché au processus ; c'est
  pourquoi il y a trois serveurs MCP, et non un seul qui lirait le profil dans le jeton.

## 📖 Glossaire

- **Conteneur** — un processus isolé qui embarque son propre système de fichiers ; ici,
  un par service.
- **Image** — le modèle figé dont on tire un conteneur. Construite par le `Dockerfile`.
- **Volume** — un dossier géré par Docker qui survit à la destruction du conteneur.
- **Reverse-proxy** — un serveur placé devant l'app, qui reçoit le public et lui transmet
  les requêtes. Caddy joue ce rôle, et obtient le certificat HTTPS tout seul.
- **`basic_auth`** — l'authentification la plus simple du web : un identifiant et un mot de
  passe demandés par le navigateur avant d'afficher la page.
- **bcrypt** — une fonction qui transforme un mot de passe en empreinte irréversible ; le
  serveur compare des empreintes, il ne connaît jamais le mot de passe.
- **`sslip.io`** — un service DNS public qui fait pointer `quelquechose.178-104-184-125.sslip.io`
  vers l'IP `178.104.184.125`. Il permet un certificat HTTPS sans acheter de domaine.
- **502** — la réponse d'un reverse-proxy dont le serveur d'en face ne répond pas ; ici, le
  signe que l'app est arrêtée alors que Caddy tourne encore.
