# Mettre la gateway en ligne

Trois conteneurs sur un serveur Linux avec Docker : **l'app** (interface web, serveur MCP
lancé en sous-processus, scripts de mise en place), **PostgreSQL** (les cinq barrières
Text-to-SQL restent intactes), et **Caddy** devant, pour le HTTPS automatique et un mot de
passe. Rien n'est simulé : c'est le même code qu'en local, avec la même base.

Le résultat est une adresse `https://…` que le formateur ouvre avec un identifiant et un
mot de passe transmis à part. Il y teste les trois chantiers : RAG, Text-to-SQL, et le
panneau MCP qui lance un vrai serveur à chaque clic.

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

Image : 1,13 Go, sans modèle à télécharger — l'embedder livré est un hachage local.

## Les fichiers

| Fichier | Rôle |
|---|---|
| `../Dockerfile` | l'image de l'app : Python 3.11, dépendances par `uv`, sans l'extra `vector` |
| `../.dockerignore` | ce qui n'entre jamais dans l'image : `.env`, `.git`, tests, livrables |
| `demarrer.sh` | au démarrage : base SQLite, index, migrations + import PostgreSQL, puis `uvicorn` |
| `compose.prod.yml` | les trois services, les volumes, les variables |
| `Caddyfile` | HTTPS + `basic_auth` |
| `.env.prod.example` | le modèle des variables ; `.env.prod` est ignoré par git |

## Procédure

Deux endroits, et il ne faut pas les confondre :

- 💻 **TON PC** — PowerShell local
- 🖧 **LE SERVEUR** — après `ssh root@<ip>`

### 1 · Se connecter au serveur

💻 **TON PC**

```
ssh root@116.203.244.44
```

Si SSH refuse avec `REMOTE HOST IDENTIFICATION HAS CHANGED`, c'est que le serveur a été
réinstallé depuis la dernière connexion. **Vérifier d'abord dans la console Hetzner que
c'est bien le cas**, puis seulement :

```
ssh-keygen -R 116.203.244.44
```

et recommencer la connexion.

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
| `SORABEL_HOTE` | `116-203-244-44.sslip.io`, ou le nom de domaine s'il y en a un |
| `SORABEL_POSTGRES_PASSWORD` | premier `openssl rand` |
| `SORABEL_SUPPORT_PASSWORD` | deuxième |
| `SORABEL_COMMERCIAL_PASSWORD` | troisième |
| `SORABEL_SQL_GENERATOR` | `openai_compatible` pour gpt-5.4 comme en démo, `deterministic` sans clé |
| `SORABEL_SQL_LLM_*` | l'adresse, le modèle et la clé Azure — seulement si `openai_compatible` |

### 4 · Le mot de passe du formateur

Caddy ne stocke pas le mot de passe : il stocke son empreinte bcrypt. La produire :

🖧 **LE SERVEUR**

```
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'LE_MOT_DE_PASSE_CHOISI'
```

Copier la sortie (elle commence par `$2a$14$`) à la place de `HASH_A_REMPLACER` :

```
nano deploy/Caddyfile
```

L'identifiant est `formateur` ; il se change sur la même ligne.

### 5 · Lancer

🖧 **LE SERVEUR**

```
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml up -d --build
```

La première fois, la construction prend quelques minutes. Suivre le démarrage de l'app :

```
docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml logs -f app
```

Les quatre étapes `[1/4]` à `[4/4]` doivent défiler, puis `Uvicorn running`. `Ctrl+C` quitte
le suivi sans arrêter les conteneurs.

### 6 · Vérifier — ne pas s'en passer

💻 **TON PC**

```
curl -sS -o /dev/null -w "%{http_code}\n" https://116-203-244-44.sslip.io/
```

Attendu : **401**. C'est le bon résultat — la page existe, elle demande le mot de passe.

```
curl -sS -o /dev/null -w "%{http_code}\n" -u formateur:LE_MOT_DE_PASSE_CHOISI https://116-203-244-44.sslip.io/
```

Attendu : **200**. Puis ouvrir l'adresse dans un navigateur, entrer l'identifiant, et
rejouer la question « quelle est la marge sur la REF-8842 ? » en profil support puis
commercial. Si le certificat HTTPS met une minute à apparaître, c'est Let's Encrypt qui
l'émet : attendre, ne pas relancer.

### 7 · Transmettre au formateur

Le lien, l'identifiant `formateur` et le mot de passe — **par un canal séparé du message
qui donne le lien**. Le dépôt GitHub ne contient ni l'un ni l'autre.

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
rejouables sans dommage.

## Couper l'accès quand le formateur a fini

Le déploiement est fait pour être **temporaire**. Trois niveaux, du plus doux au plus
radical — tous depuis le dossier du dépôt.

🖧 **LE SERVEUR**

```
cd /opt/sorabel
```

| Niveau | Commande | Effet |
|---|---|---|
| **1 · Fermer la porte** | `docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml stop caddy` | le site ne répond plus ; l'app et la base restent en place. `start caddy` rouvre en 2 s |
| **2 · Tout éteindre** | `docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml down` | les trois conteneurs s'arrêtent ; les volumes (base, journal, certificat) sont conservés |
| **3 · Tout effacer** | `docker compose --env-file deploy/.env.prod -f deploy/compose.prod.yml down -v` | plus rien ne reste, sauf le code cloné |

Vérifier, depuis le PC, que la porte est bien fermée :

💻 **TON PC**

```
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 10 https://116-203-244-44.sslip.io/
```

Attendu après le niveau 1 : **000** (connexion refusée) — plus de 401, plus de 200.

Après le niveau 3, penser aussi à **révoquer la clé Azure** dans le portail si elle avait
été mise dans `deploy/.env.prod` : un secret qui a vécu sur un serveur se remplace.

## Ce que ce déploiement ne fait pas

- **Pas d'authentification par utilisateur.** Le mot de passe Caddy protège l'accès à la
  page ; le profil se choisit ensuite dans l'interface, comme en local. Brancher un
  fournisseur d'identité reste la limite documentée du projet.
- **Pas de serveur MCP joignable à distance.** Le serveur MCP parle `stdio` et n'est lancé
  que par l'interface, dans le conteneur. Un IDE externe ne peut pas s'y brancher.

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
- **`sslip.io`** — un service DNS public qui fait pointer `a-b-c-d.sslip.io` vers l'IP
  `a.b.c.d`. Il permet un certificat HTTPS sans acheter de domaine.
