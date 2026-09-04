# Interface — preuves des résultats

## Objectif

Simplifier l'interface de démonstration et permettre au lecteur de vérifier l'origine de chaque
résultat. La zone de questions préremplies est supprimée. L'interface distingue les preuves
documentaires du RAG des preuves d'exécution de Text-to-SQL.

## Périmètre

- supprimer la section « Questions de démonstration » et ses boutons ;
- conserver la saisie manuelle et les profils Support, Commercial et Developer ;
- enrichir uniquement le rendu des réponses déjà renvoyées par le serveur ;
- ne pas modifier la logique métier RAG, SQL, MCP ou les droits d'accès.

## Preuve RAG

Une réponse RAG affiche une section **Sources**. Chaque source contient exclusivement les champs
reçus du serveur :

- titre du document ;
- référence produit ;
- date du document.

Ces trois indicateurs permettent de retrouver la preuve dans le corpus. Si la preuve est
insuffisante, le serveur renvoie `hors_corpus` et l'interface n'affiche aucune réponse métier
inventée.

## Preuve Text-to-SQL

Un résultat SQL affiche un résumé **Execution proof** toujours visible avec :

- backend d'exécution ;
- vue ou ressource sémantique autorisée, extraite de la requête renvoyée ;
- colonnes retournées ;
- nombre de lignes ;
- date logique du dataset (`data_as_of`) ;
- versions du dataset, du schéma sémantique et de la politique.

Un bloc natif dépliable **Technical details** contient la requête SQL exacte et ses paramètres.
La vue affichée est dérivée de la requête reçue ; elle n'est pas inventée par le navigateur.

## Refus et erreurs

Un refus affiche le code typé renvoyé par le serveur, par exemple `UNSAFE_SQL`,
`NOT_AUTHORIZED`, `OUT_OF_SCHEMA` ou `AMBIGUOUS_QUESTION`. Il précise qu'aucune requête n'a été
exécutée et qu'aucune donnée métier n'a été produite. Aucun détail sensible ou ressource cachée
n'est révélé.

## Règles d'interface

- résumé de preuve visible sans clic ;
- détails techniques accessibles par clavier avec l'élément HTML `details` ;
- libellés explicites, sans dépendre uniquement de la couleur ;
- valeurs indisponibles omises plutôt que remplacées par des informations supposées ;
- aucune preuve, réponse ou erreur fabriquée côté navigateur.

## Critères d'acceptation

1. La section des questions de démonstration n'existe plus dans le HTML ni dans le JavaScript.
2. Une réponse RAG couverte affiche titre, référence et date.
3. Un résultat SQL affiche son résumé de preuve et permet d'ouvrir SQL et paramètres.
4. Une vue sémantique affichée correspond à une ressource présente dans le SQL renvoyé.
5. Un refus affiche son code et confirme l'absence d'exécution et de donnée métier.
6. Les tests Web, RAG, SQL, MCP, Ruff et mypy continuent de passer.
