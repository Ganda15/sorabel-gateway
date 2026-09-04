# Interface de démonstration Sorabel — conception

## Objectif

Faire de l’interface Web locale une preuve lisible du fonctionnement de Sorabel pendant la démonstration. Un lecteur doit pouvoir distinguer immédiatement le RAG du Text-to-SQL, comprendre l’effet du profil actif et vérifier pourquoi une réponse, un résultat SQL ou un refus est fiable.

## Périmètre

La modification concerne uniquement la présentation et l’interaction dans :

- `web_app/static/index.html` ;
- `web_app/static/styles.css` ;
- `web_app/static/app.js` ;
- les tests d’intégration Web nécessaires.

Les routes FastAPI, les contrats communs, les services RAG, Text-to-SQL, PostgreSQL et MCP restent inchangés. Aucun framework frontal et aucune dépendance d’exécution supplémentaire ne sont ajoutés.

UI UX Pro Max sert de guide de conception ponctuel. Il ne devient ni une bibliothèque embarquée, ni une dépendance du livrable.

## Architecture de l’écran

L’écran conserve une seule page et rend le parcours visible dans cet ordre :

1. choix du profil authentifié simulé : Support, Commercial ou Developer ;
2. choix du domaine : Documents · RAG ou Données · SQL ;
3. affichage du périmètre associé au profil et au domaine ;
4. saisie manuelle ou sélection d’un exemple démontrable ;
5. appel de la route existante ;
6. résultat typé avec ses preuves ou motif de refus.

Une courte bande de parcours rappelle : `Profil → Outil → Contrôle → Résultat vérifiable`.

## Composants

### Sélecteurs et périmètre

Les sélecteurs existants sont conservés. Un panneau de contexte explique, pour la combinaison active, l’outil réellement appelé et les garanties principales. Le profil Developer continue d’obtenir la recherche documentaire décomposée ou le schéma SQL visible, sans réponse métier simulée.

### Exemples de démonstration

Des boutons d’exemple injectent une question dans le champ sans l’envoyer automatiquement. Les exemples changent selon le mode et le profil afin d’éviter de présenter une question incompatible comme un cas nominal.

Les cas couverts sont :

- RAG couvert avec citation ;
- RAG hors corpus ;
- SQL analytique autorisé ;
- stock par référence ;
- tentative d’écriture refusée ;
- donnée sensible refusée pour Support ;
- question hors schéma.

### Résultats typés

Les sorties utilisent des traitements visuels distincts :

- RAG vérifié : réponse, titre, référence et date ;
- recherche Developer : passages classés et métadonnées ;
- SQL en lecture seule : lignes, requête SQL et versions ;
- schéma Developer : vues et colonnes autorisées ;
- refus : statut, code métier quand il est fourni, explication et confirmation qu’aucun résultat métier n’est présenté ;
- erreur technique : message contrôlé, différent d’un refus métier.

Le texte de la question n’est jamais présenté comme une réponse. Un refus n’affiche ni citation documentaire ni faux résultat SQL.

## Flux de données

Le JavaScript choisit toujours une route déjà existante :

- Support ou Commercial + RAG → `/api/answer` ;
- Developer + RAG → `/api/search` ;
- Support ou Commercial + SQL → `/api/database` ;
- Developer + SQL → `/api/schema`.

La réponse conserve l’enveloppe commune `status`, `payload`, `message`. Le rendu dépend exclusivement du statut et de la forme du payload ; aucune réponse métier n’est fabriquée dans le navigateur.

## Gestion des erreurs et refus

Les statuts `hors_corpus`, `refused`, `clarification` et `invalid_request` sont rendus comme des refus contrôlés. `execution_error` est rendu comme une erreur technique. Le bouton est désactivé pendant l’appel puis réactivé dans tous les cas.

Lorsque `payload.error_code` existe, l’interface l’affiche. Dans le cas contraire, elle affiche le statut de l’enveloppe sans inventer un code.

## Accessibilité et adaptation

- contraste lisible et information jamais portée par la couleur seule ;
- focus clavier visible ;
- vrais boutons pour les exemples ;
- zone de résultat annoncée avec `aria-live` ;
- état de chargement accessible ;
- mise en page testée aux largeurs 375, 768, 1024 et 1440 px ;
- respect de `prefers-reduced-motion` ;
- identifiants, SQL et libellés longs capables de revenir à la ligne sans être tronqués.

## Tests et critères d’acceptation

Le développement suit TDD. Les tests Web sont ajoutés avant le code pour vérifier :

1. la présence des contrôles et exemples accessibles ;
2. la séparation visuelle et sémantique des modes RAG et SQL ;
3. l’affichage des preuves RAG ;
4. l’affichage de la requête et des versions SQL ;
5. l’affichage explicite des refus sans résultat métier ;
6. la conservation des quatre routes et de leurs profils autorisés.

Après les tests ciblés, l’ensemble des tests unitaires, d’intégration et d’acceptance RAG, SQL et MCP est relancé. Une vérification manuelle confirme les scénarios de démonstration dans le navigateur.

## Hors périmètre

- remplacement de FastAPI ;
- migration vers Gradio, React ou Tailwind ;
- modification des règles d’accès ;
- ajout de Keycloak dans cette itération ;
- modification du moteur RAG, de la génération SQL ou des données ;
- ajout d’une conversation persistante.
