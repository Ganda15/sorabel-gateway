# Dossier de conception — point d’entrée unique

Ce dossier contient les **cinq éléments de conception** reliés directement au code et aux tests du
dépôt. Il constitue la lecture formateur autonome.

## Ordre de lecture

1. [Schéma du flux complet](01-schema-flux-complet.md)
2. [Modèle des chunks et métadonnées](02-modele-chunks-metadonnees.md)
3. [Catalogue des huit tools MCP](03-catalogue-tools-mcp.md)
4. [Chemin Text-to-SQL](04-chemin-text-to-sql.md)
5. [Matrice d’accès](05-matrice-acces.md)

## Principe commun

```text
L’Agent choisit le tool
        ↓
la Gateway autorise l’appel
        ↓
le service RAG ou SQL applique le périmètre
        ↓
la sortie est contrôlée
        ↓
le succès ou le refus est audité
```

La conception n’est plus présentée comme trois systèmes indépendants. Les chantiers ont des
responsabilités différentes, mais ils forment une seule Sorabel Data Gateway :

- chantier 1 prépare et recherche les preuves documentaires ;
- chantier 2 interroge les données structurées en lecture seule ;
- chantier 3 expose et gouverne les huit tools pour tous les clients.

## Statut vérifiable

- RAG avancé, Text-to-SQL PostgreSQL, Gateway MCP et interface Web : implémentés ;
- authentification Keycloak : architecture cible, non implémentée dans ce dépôt ;
- chaque affirmation chiffrée doit être confirmée par une exécution récente des tests ou des
  rapports présents dans `eval/` et `docs/livrable/evidence/`.
