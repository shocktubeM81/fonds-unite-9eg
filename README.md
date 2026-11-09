# Fonds d’unité du 9 EG — établissement 5422

**Projet de constitution — non approuvé.**

Ce dépôt encadre le fonds existant de Rouyn-Noranda, identifié par le code comptable **5422**, au bénéfice du personnel du 9e Escadron du génie. Il documente sa gouvernance et sa distinction avec le fonds du 34 RGC rattaché à **5246**.

## Documents

- [Projet de constitution](constitution-projet.md)
- [Points à valider](documentation/points-a-valider.md)
- [Historique des révisions](documentation/historique.md)

Le libellé officiel recensé pour 5422 est « RESERVE-BRN-34CBG5050-UNITÉ-34 RGC-ROUYN-NORANDA ». L’appellation locale « Fonds d’unité du 9 EG » ne modifie pas à elle seule ce libellé ni les délégations applicables.

## Révision et approbation

Proposer les changements sur une branche `codex/description-courte`, puis les faire relire dans une demande de fusion. Décrire la disposition touchée, le motif et les validations nécessaires. Une fusion GitHub ne constitue pas une approbation administrative.

Après approbation, consigner les dates réelles, les références des décisions et la version exacte approuvée. Conserver les justificatifs sensibles dans l’espace officiel à accès contrôlé.

Ce dépôt public contient les textes généraux et leur historique. Les coordonnées bancaires, renseignements personnels, pièces comptables et dossiers individuels restent dans les systèmes autorisés.

## Site documentaire

Le site reprend la présentation du Mess avec cinq rubriques : accueil, constitution, références, points à valider et historique. Il propose un sommaire, une lecture sur téléphone et une mise en page pour l’impression.

La constitution et les documents du dossier `documentation/` restent les sources du site. Le générateur `site/build.mjs` produit les pages dans `dist/` et vérifie leurs liens locaux. Les références sont extraites directement de la constitution.

Pour construire le site : installer Node.js 24 et pnpm 11.25.0, puis exécuter `pnpm install --frozen-lockfile` et `pnpm run build`.

Le workflow GitHub vérifie les demandes de fusion et publie les modifications de `main` sur GitHub Pages. L’hébergement utilise GitHub Actions. Le domaine personnalisé est `fonds.9eg.ca`; le fichier `CNAME` est inclus dans les pages produites.

Dans Cloudflare, le sous-domaine `fonds` doit avoir un enregistrement CNAME vers `shocktubem81.github.io`, en mode « DNS uniquement », avec une durée de vie automatique. GitHub Pages doit également être configuré pour `fonds.9eg.ca`. L’activation de HTTPS dépend de la validation du pointage et du certificat par GitHub.
