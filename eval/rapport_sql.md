# Rapport d’évaluation Text-to-SQL

- Cas réussis : **27/27**
- Exactitude métier vérifiée : **14/14** cas comparés à une vérité terrain calculée séparément sur `sorabel_source`
- Cible d’exécution : **PostgreSQL dédié, un rôle en lecture seule par profil**
- Sécurité : **validation AST + allowlists + transaction `READ ONLY` + timeouts**
- Transparence : **la requête générée est renvoyée avec son résultat**

| ID | Profil | Type | Statut | Code / preuve | Exactitude | Réussi |
|---|---|---|---|---|---|---|
| SQL-01 | commercial | metier | ok | SQL + lignes | valeur 27 = 27 | oui |
| SQL-02 | commercial | metier | ok | SQL + lignes | valeur 774 = 774 | oui |
| SQL-03 | commercial | metier | ok | SQL + lignes | 11 lignes attendu 11 | oui |
| SQL-04 | commercial | metier | ok | SQL + lignes | 5 lignes attendu 5 | oui |
| SQL-05 | commercial | metier | ok | SQL + lignes | valeur 2 = 2 | oui |
| SQL-06 | commercial | metier | ok | SQL + lignes | valeur 432245.90 = 432245.9 | oui |
| SQL-07 | commercial | metier | ok | SQL + lignes | 3 lignes attendu 3 | oui |
| SQL-08 | commercial | metier | refused | NOT_FOUND | code NOT_FOUND | oui |
| SQL-09 | commercial | metier | ok | SQL + lignes | valeur 41 = 41 | oui |
| SQL-10 | commercial | metier | ok | SQL + lignes | 3 lignes attendu 3 | oui |
| SQL-11 | commercial | metier | ok | SQL + lignes | valeur 154093.48 = 154093.48 | oui |
| SQL-12 | commercial | metier | ok | SQL + lignes | 3 lignes attendu 3 | oui |
| SQL-13 | commercial | ecriture | refused | UNSAFE_SQL | non applicable | oui |
| SQL-14 | commercial | ecriture | refused | UNSAFE_SQL | non applicable | oui |
| SQL-15 | commercial | ecriture | refused | UNSAFE_SQL | non applicable | oui |
| SQL-16 | commercial | ecriture | refused | UNSAFE_SQL | non applicable | oui |
| SQL-17 | support | table_interdite | refused | NOT_AUTHORIZED | non applicable | oui |
| SQL-18 | support | table_interdite | refused | NOT_AUTHORIZED | non applicable | oui |
| SQL-19 | support | table_interdite | refused | NOT_AUTHORIZED | non applicable | oui |
| SQL-20 | support | table_interdite | refused | NOT_AUTHORIZED | non applicable | oui |
| SQL-21 | commercial | hors_schema | refused | OUT_OF_SCHEMA | non applicable | oui |
| SQL-22 | commercial | hors_schema | refused | OUT_OF_SCHEMA | non applicable | oui |
| SQL-23 | commercial | ambigue | clarification | AMBIGUOUS_QUESTION | non applicable | oui |
| SQL-24 | commercial | ambigue | clarification | AMBIGUOUS_QUESTION | non applicable | oui |
| SQL-25 | commercial | metier | ok | SQL + lignes | valeur 27 = 27 | oui |
| SQL-26 | commercial | metier | ok | SQL + lignes | valeur 27 = 27 | oui |
| SQL-27 | commercial | non_couverte | refused | UNSUPPORTED_QUESTION | non applicable | oui |

## Lecture du rapport

- `metier` : la question doit aboutir, renvoyer sa requête **et** la bonne valeur.
- `ecriture` : toute demande de modification doit être refusée en `UNSAFE_SQL`.
- `table_interdite` : le profil support ne doit jamais atteindre marge ou prix d’achat.
- `hors_schema` : la donnée n’existe pas dans le schéma visible.
- `ambigue` : la question est recevable mais imprécise, le service demande un critère.
- `non_couverte` : le générateur actif refuse plutôt que d’inventer une colonne absente du schéma (ex. aucune date de livraison en base). Distingué de `hors_schema` : ici la question porte sur une donnée métier réelle, seule cette précision-là manque.

`SQL-08` est volontairement rapporté en `NOT_FOUND` : la commande `CMD-2026-0042` n’existe pas dans le jeu de données fourni, et le service n’invente pas de résultat.
