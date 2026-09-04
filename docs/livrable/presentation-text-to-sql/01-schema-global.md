# 1 — Présenter les deux schémas Text-to-SQL

Cette partie concerne le **chantier Text-to-SQL**. La Gateway apparaît seulement comme porte
d’entrée : elle transmet au service le profil et son périmètre SQL. Le sujet principal reste le
service SQL, ses quatre tools et ses garanties.

## Schéma A — architecture d’implémentation

![Architecture Text-to-SQL centrée sur SqlService](../architecture/diagrams/09-architecture-text-to-sql-centree-service.svg)

### Comment le lire

Lire **du centre vers l’extérieur**. Le cercle `SqlService commun` est le cœur du chantier. Chaque
branche répond ensuite à une question différente : qui entre, quels tools existent, quelles routes
sont possibles, quelles données sont visibles, quels contrôles s’appliquent et que contient la
réponse.

Dans la présentation, une légende indépendante est placée sous le schéma : vert pour le service
central, jaune pour l’entrée et l’accès, orange pour les tools SQL, bleu clair pour les routes, bleu
pour la source sémantique et violet pour les contrôles et le contrat de réponse. Elle n’est pas
reliée au service : ce n’est pas un composant de l’architecture.

1. Commencer au centre : les quatre tools utilisent le même `SqlService`.
2. Suivre la branche **Entrée et accès** : la Gateway vérifie l’accès au tool SQL et transmet le
   périmètre du profil. Elle ne génère pas de SQL.
3. Suivre la branche **Quatre tools SQL** :
   `get_schema`, `check_stock`, `order_status` et `ask_database`.
4. Suivre la branche **Trois routes** : catalogue seul, requête figée ou analyse
   variable.
5. Terminer par **Source sémantique**, **Défense en profondeur** et **Contrat de réponse**.

### Pourquoi cette organisation

- La **Gateway** décide si l’appel est autorisé.
- Le **SqlService** orchestre le comportement du tool.
- Le **Generator** propose une requête ; il n’accorde jamais un droit.
- Le **SqlValidator** vérifie l’AST, les objets autorisés et la limite.
- **PostgreSQL** impose encore le rôle, `GRANT SELECT`, la transaction `READ ONLY` et les timeouts.

Phrase orale :

> La Gateway contrôle l’entrée. Les quatre tools partagent un SqlService. Le service choisit une
> route, puis la validation et PostgreSQL empêchent qu’une proposition devienne une action non
> autorisée.

## Schéma B — chemin exact de `ask_database`

![Chemin exact de ask_database](../architecture/diagrams/10-chemin-exact-ask-database.svg)

### Comment le lire

Lire **de haut en bas**. Chaque colonne représente un composant. Une flèche pleine est un appel ;
une flèche pointillée est un retour.

Dans ce schéma, le vert identifie les composants, le jaune les règles et contextes, et l’orange les
branches alternatives qui peuvent conduire à un refus ou à une exécution.

1. **Entrée et autorisation** : la Gateway reçoit `ask_database(question, profil)` et contrôle
   l’accès au tool.
2. **Contexte filtré** : le `SqlService` demande uniquement les vues, colonnes, KPI et versions du
   profil.
3. **Décision** :
   - écriture, donnée sensible, hors schéma ou ambiguïté → erreur typée, aucune ligne ;
   - stock ou statut reconnu → requête figée paramétrée ;
   - analyse variable autorisée → proposition SQL du Generator.
4. **Validation et exécution** : l’AST et les allowlists sont contrôlés, puis PostgreSQL exécute
   avec le compte du profil dans une transaction `READ ONLY`.
5. **Retour** : les colonnes sont contrôlées et le client reçoit résultat, SQL, paramètres,
   versions, `request_id` et trace d’audit.

Phrase orale :

> La question descend dans le temps. Un refus s’arrête avant PostgreSQL. Seule une demande
> autorisée atteint le validateur puis la base, et son résultat revient avec les éléments qui
> permettent de le vérifier.

## Fichiers des schémas

| Schéma | SVG zoomable | PNG | Source Mermaid |
|---|---|---|---|
| Architecture Text-to-SQL | [SVG](../architecture/diagrams/09-architecture-text-to-sql-centree-service.svg) | [PNG](../architecture/diagrams/09-architecture-text-to-sql-centree-service.png) | [MMD](../architecture/diagrams/09-architecture-text-to-sql-centree-service.mmd) |
| Séquence `ask_database` | [SVG](../architecture/diagrams/10-chemin-exact-ask-database.svg) | [PNG](../architecture/diagrams/10-chemin-exact-ask-database.png) | [MMD](../architecture/diagrams/10-chemin-exact-ask-database.mmd) |

## Transition vers le code

> Maintenant que les responsabilités et le sens des flèches sont clairs, je montre le code qui
> prouve chaque bloc, puis je termine par la démonstration Sorabel Assistant.
