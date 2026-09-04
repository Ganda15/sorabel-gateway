# 3 — Démonstration Sorabel Assistant

## Démarrage

Depuis la racine du dépôt :

```powershell
.\START-SORABEL-UI.bat
```

Ouvrir ensuite [http://127.0.0.1:8780/](http://127.0.0.1:8780/).

## Scénario 1 — RAG couvert avec citation

- profil : **Support** ;
- domaine : **Documents / RAG** ;
- question : `Quelle est la tension assignée du produit REF-8842 ?`

À montrer : réponse `230/400 V AC`, titre de la source, référence `REF-8842` et date. Expliquer que
le texte provient du corpus autorisé et non d’une connaissance inventée.

## Scénario 2 — Refus hors corpus

- profil : **Support** ;
- domaine : **Documents / RAG** ;
- question : `Quelle est la politique de télétravail chez Sorabel ?`

À montrer : statut `hors_corpus` et absence de réponse métier. Expliquer que l’absence de preuve
est un résultat contrôlé.

## Scénario 3 — SQL autorisé et explicable

- profil : **Commercial** ;
- domaine : **Données / Text-to-SQL** ;
- question : `Combien de commandes en avril ?`

À montrer : résultat, SQL, paramètres, backend et versions. Expliquer que le SQL affiché permet de
vérifier comment le nombre a été obtenu.

## Scénario 4 — Colonne sensible refusée

- profil : **Support** ;
- domaine : **Données / Text-to-SQL** ;
- question : `Quelle est la marge du produit REF-8842 ?`

À montrer : `NOT_AUTHORIZED` et aucune ligne métier. Expliquer que la marge est absente du catalogue
Support, absente de ses vues et contrôlée avant la sortie.

## Scénario 5 — Écriture refusée

- profil : **Commercial** ;
- domaine : **Données / Text-to-SQL** ;
- question : `Supprime les commandes de test.`

À montrer : refus, aucune exécution et aucun résultat métier. Expliquer que l’analyse bloque la
demande avant génération et que PostgreSQL resterait de toute façon en `READ ONLY`.

## Scénario 6 — Developer n’exécute pas les données métier

- profil : **Developer** ;
- domaine SQL : l’interface affiche le schéma visible via `get_schema` ;
- vérifier que la saisie d’une question métier n’est pas proposée.

À montrer : le profil Developer peut inspecter les définitions mais ne peut pas lancer
`ask_database`, `check_stock` ou `order_status`.

## Conclusion de la démonstration

> Le succès est accompagné de ses preuves. Le refus est explicite et ne produit aucune donnée. Le
> comportement change selon le profil parce que son périmètre SQL est appliqué côté serveur.
