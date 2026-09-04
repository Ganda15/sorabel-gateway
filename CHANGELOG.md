# Journal des modifications

Les modifications importantes du projet sont consignées ici. Les résultats mesurés sont ajoutés uniquement après l’exécution réussie de la commande correspondante.

## Non publié

### Ajouté

- conservation du starter intact au commit `c759d06` avec le tag `before-rag-development` ;
- création de la branche de développement `feature/rag-avance` ;
- ajout de la conception validée du RAG avancé local ;
- ajout des règles de travail et des checklists de développement ;
- regroupement des schémas Mermaid et de la présentation exécutable dans `docs/livrable` ;
- modèles canoniques des documents, chunks, résultats et citations ;
- parseurs PDF, HTML et Markdown avec métadonnées normalisées ;
- catalogue de versions, détection de doublons et chunking déterministe ;
- pipeline d’ingestion et manifeste local ;
- recherche dense locale, BM25, fusion RRF et reranking interchangeable ;
- adaptateur Chroma idempotent et embedder multilingue optionnel ;
- CLI RAG, évaluation E6 et rapport de gain chiffré ;
- serveur MCP stdio, huit tools, matrice initiale et audit JSONL.
- interface Web unifiée connectée à la même Gateway applicative ;
- source PostgreSQL dédiée, cinq tables réconciliées, vues sémantiques et rôles lecteurs ;
- analyse, génération, validation AST, allowlists, bornes et exécution SQL read-only ;
- quatre tools SQL et évaluation reproductible de 24 cas ;
- dossier final des cinq conceptions, traçabilité et présentation complète sans notes privées ;
- séparation stricte du périmètre officiel versionné.

### État actuel

- conception et préparation du dépôt local : terminées ;
- implémentation du RAG avancé terminal : terminée et vérifiée ;
- dernière vérification locale du 2026-09-04, après le chantier 3 : **209 tests réussis**
  (149 unitaires · 12 d’acceptance · 48 d’intégration) ;
- génération SQL **agentique** par défaut (`gpt-5.4` via Azure AI Foundry) ; le générateur
  déterministe reste disponible en repli hors ligne via `SORABEL_SQL_GENERATOR` ;
- évaluation Text-to-SQL portée à **27 cas sur 27**, dont **14 exactitudes métier sur 14** ;
- mesure Recall@1 : dense 0,727 ; hybride 0,818 ; gain +9,1 points ;
- interface graphique unifiée : implémentée dans `web_app/` ;
- Text-to-SQL : PostgreSQL, source sémantique, rôles, AST, tools et preuves implémentés ;
- évaluation Text-to-SQL : **27 cas sur 27**, dont **14 exactitudes métier** comparées à
  une vérité terrain calculée séparément sur `sorabel_source` ;
- code d’erreur `UNSUPPORTED_QUESTION` distinct de `OUT_OF_SCHEMA` : une formulation non
  couverte par le générateur n’est plus annoncée comme une donnée absente du schéma ;
- journal d’audit commun aux deux adaptateurs (`application/audit.py`) : le chemin Web
  journalise comme le chemin MCP, avec la question, le SQL et la durée ;
- une question d’agrégation (« stock **total** ») n’est plus routée vers le tool figé, qui
  renvoyait un détail par entrepôt au lieu de la somme demandée ;
- Gateway MCP : huit tools, matrice et audit implémentés ; Keycloak et le filtrage natif de
  `tools/list` par session restent à industrialiser.
