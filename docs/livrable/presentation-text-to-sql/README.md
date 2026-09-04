# Présentation Text-to-SQL — schémas, code, démonstration

Ce dossier donne un ordre strict pour présenter l’implémentation sans lire tout le dépôt.
L’interface fonctionnelle n’est pas modifiée par ce support.

## Ordre recommandé

1. [Deux schémas Text-to-SQL et lecture guidée](01-schema-global.md) — montrer l’architecture
   puis le chemin de `ask_database`.
2. [Explication des fichiers importants](02-explication-code.md) — prouver chaque décision.
3. [Démonstration Sorabel Assistant](03-demo-sorabel-assistant.md) — montrer les comportements.

## Supports visuels Text-to-SQL

- [Architecture centrée sur le SqlService — SVG](../architecture/diagrams/09-architecture-text-to-sql-centree-service.svg)
- [Architecture centrée sur le SqlService — PNG](../architecture/diagrams/09-architecture-text-to-sql-centree-service.png)
- [Architecture centrée sur le SqlService — source Mermaid](../architecture/diagrams/09-architecture-text-to-sql-centree-service.mmd)
- [Séquence exacte de ask_database — SVG](../architecture/diagrams/10-chemin-exact-ask-database.svg)
- [Séquence exacte de ask_database — PNG](../architecture/diagrams/10-chemin-exact-ask-database.png)
- [Séquence exacte de ask_database — source Mermaid](../architecture/diagrams/10-chemin-exact-ask-database.mmd)
- [Architecture technique d’exécution — SVG](../architecture/diagrams/11-architecture-technique-execution.svg)
- [Architecture technique d’exécution — PNG](../architecture/diagrams/11-architecture-technique-execution.png)
- [Architecture technique d’exécution — source Mermaid](../architecture/diagrams/11-architecture-technique-execution.mmd)

## Durée conseillée

| Partie | Durée | Résultat attendu |
|---|---:|---|
| Schémas | 3 min | comprendre les quatre tools, les trois routes et le chemin de `ask_database` |
| Code | 4 min | relier chaque choix important à une preuve dans le dépôt |
| Démonstration | 3 min | montrer succès, source, SQL et refus |

La version bilingue et les réponses aux questions sont conservées hors du dépôt, dans le dossier
privé `04-STUDY-GUIDES/chantier-2/sorabel-gateway-private/`. Elles ne font pas partie du livrable
public ni du push GitHub.
