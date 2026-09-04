# Traçabilité — brief local, conception, code et preuves

Ce document répond à une seule question : **où chaque exigence est-elle conçue, implémentée et
prouvée ?** La source fonctionnelle utilisée est `docs/cadrage_dsi.md` dans ce dépôt.

## Exigences E1 à E6

| Exigence | Conception | Implémentation | Test / preuve | État |
|---|---|---|---|---|
| E1 — citations et refus hors corpus | `conception/02-modele-chunks-metadonnees.md` | `retrieval/service.py`, `retrieval/models.py` | `tests/acceptance/test_rag.py` | implémenté |
| E2 — référence exacte et langage naturel | `conception/01-schema-flux-complet.md` | `retrieval/dense.py`, `lexical.py`, `fusion.py` | top-1 REF-8842 dans l’acceptance | implémenté |
| E3 — SQL read-only, périmètre, transparence | `conception/04-chemin-text-to-sql.md` | `sql/validator.py`, `executors.py`, `service.py` | `tests/acceptance/test_sql.py` | implémenté |
| E4 — un serveur MCP et matrice | `conception/03-catalogue-tools-mcp.md`, `05-matrice-acces.md` | `application/access_policy.json` (source unique), `application/policy.py`, `application/gateway.py`, `mcp_server/server.py` | `tests/acceptance/test_mcp.py`, `tests/integration/test_mcp_catalogue.py`, `tests/unit/test_access_policy.py` | implémenté — `tools/list` filtré **et** appel réautorisé ; identité de démonstration par variable d’environnement |
| E5 — audit et aucune marge Support | `conception/05-matrice-acces.md` | `application/audit.py`, `mcp_server/server.py`, `sql/service.py`, rôles PostgreSQL | tests SQL/MCP + preuve RBAC + `docs/livrable/evidence/mcp-demonstration.json` | implémenté — 8 appels, 8 lignes de journal |
| E6 — gain RAG mesuré | architecture RAG | `retrieval/evaluation.py`, `scripts/evaluate_rag.py` | `eval/rapport_gain.md` | implémenté |

## Livrables demandés

| Élément | Emplacement officiel dans le dépôt |
|---|---|
| schéma du flux complet | `docs/livrable/conception/01-schema-flux-complet.md` |
| modèle chunks + métadonnées | `docs/livrable/conception/02-modele-chunks-metadonnees.md` |
| catalogue des tools | `docs/livrable/conception/03-catalogue-tools-mcp.md` |
| chemin Text-to-SQL | `docs/livrable/conception/04-chemin-text-to-sql.md` |
| matrice profil × tool × ressources | `docs/livrable/conception/05-matrice-acces.md` |
| serveur MCP complet | `mcp_server/server.py` |
| mini-guide d’accès | `docs/livrable/GUIDE-ACCES-MCP.md` |
| catalogue MCP pour les équipes clientes | `docs/livrable/CATALOGUE-TOOLS-MCP.md` — **généré** depuis la politique |
| démonstration deux profils | `scripts/demo_mcp.py` → `docs/livrable/evidence/mcp-demonstration.json` |
| interface graphique | `web_app/`, démarrage avec `START-SORABEL-UI.bat` |
| preuves chiffrées | `eval/` et `docs/livrable/evidence/` |

## Tests d’acceptance

### RAG avancé

- réponse couverte avec titre, référence et date : `test_answer_question_cite_ses_sources` ;
- absence d’invention hors corpus : `test_hors_corpus_signale_sans_inventer` ;
- `REF-8842` remonte la fiche technique en tête : `test_recherche_par_reference_exacte` ;
- gain dense → hybride documenté : `test_gain_hybride_mesure_et_documente`.

### Text-to-SQL

- nombre de commandes d’avril et SQL renvoyé : `test_ask_database_repond_et_montre_sa_requete` ;
- suppression refusée et auditée : `test_ecriture_refusee_et_journalisee` ;
- marge Support refusée : `test_profil_support_jamais_de_marge` ;
- question hors schéma refusée : `test_hors_schema_refus_propre`.

### Serveur MCP

- matrice appliquée : `test_matrice_d_acces_respectee` ;
- refus clair et journalisé : `test_refus_message_clair_et_journalise` ;
- `search_docs` puis `get_document` utilisables séparément :
  `test_briques_du_rag_utilisables_separement` ;
- succès et refus présents au journal : `test_journal_exhaustif_autorises_et_refuses`.

Ajoutés le 2026-09-04, hors suite fournie (celle-ci n’a pas été modifiée) :

- le catalogue annoncé est celui de la matrice, pour les trois profils :
  `test_le_catalogue_annonce_exactement_les_tools_du_profil` ;
- le support ne voit pas `get_schema` dans `tools/list` :
  `test_le_support_ne_voit_pas_get_schema_dans_le_catalogue` ;
- chaque tool annoncé porte la description de la politique :
  `test_chaque_tool_annonce_est_livre_avec_sa_description` ;
- un tool caché reste refusé et journalisé, pas une erreur de protocole :
  `test_un_tool_hors_catalogue_reste_refuse_et_journalise` ;
- la documentation livrée ne dérive pas de la politique :
  `test_la_documentation_livree_ne_derive_pas_de_la_politique`.

## Limites annoncées honnêtement

- le moteur dense vérifié est le fallback local déterministe ; l’adaptateur Sentence Transformer
  existe mais le gain publié ne lui est pas attribué ;
- le reranker vérifié est `IdentityReranker`; un Cross Encoder est une extension ;
- Keycloak et un véritable token multi-clients ne sont pas intégrés ;
- le profil MCP de démonstration vient de `SORABEL_PROFILE` ;
- le catalogue MCP est filtré par profil **et** chaque appel est réautorisé — les deux barrières
  existent depuis le 2026-09-04 ; un `pattern` JSON Schema sur les arguments a été écarté
  volontairement : mesuré, il fait refuser l’appel au niveau protocole et le refus échappe alors
  au journal, ce qui violerait E5.

Ces limites ne sont pas des exigences présentées comme terminées. Elles définissent la prochaine
itération sans diminuer les preuves déjà exécutées.
