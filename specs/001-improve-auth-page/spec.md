# Spécification : lisibilité de la page d’authentification

**Feature Branch**: `001-improve-auth-page`

**Created**: 2026-08-01

**Status**: Implémenté et vérifié

**Input**: Demande utilisateur : commencer par améliorer la page d’authentification, dont les champs, les placeholders, les espacements et le bouton principal sont actuellement difficiles à voir.

## Scénarios utilisateur et tests

### User Story 1 - Comprendre immédiatement le formulaire (Priorité : P1)

En tant que client non technique, je veux distinguer immédiatement chaque champ et son libellé afin de savoir quelles informations saisir sans devoir deviner où cliquer.

**Pourquoi cette priorité** : l’authentification est le premier contact avec le produit. Un formulaire illisible bloque entièrement l’utilisateur.

**Test indépendant** : ouvrir la page d’inscription en thème sombre puis clair et vérifier que tous les champs sont identifiables avant toute interaction.

**Scénarios d’acceptation** :

1. **Étant donné** la page d’inscription affichée, **quand** l’utilisateur observe le formulaire, **alors** chaque champ possède une surface, une bordure, un libellé et un placeholder lisibles.
2. **Étant donné** un champ disponible, **quand** l’utilisateur le sélectionne au clavier ou à la souris, **alors** son état de focus est clairement visible.

---

### User Story 2 - Identifier l’action principale (Priorité : P2)

En tant qu’utilisateur, je veux reconnaître immédiatement le bouton de validation afin de terminer l’inscription ou la connexion sans hésitation.

**Pourquoi cette priorité** : même un formulaire correctement rempli reste inutilisable si son action principale se confond avec l’arrière-plan.

**Test indépendant** : afficher chaque mode d’authentification et vérifier que l’action principale domine visuellement les actions secondaires.

**Scénarios d’acceptation** :

1. **Étant donné** un formulaire d’authentification, **quand** il est affiché, **alors** le bouton principal est visible, lisible et possède des états de survol, de focus et de désactivation distincts.

---

### User Story 3 - Utiliser la page sur toute taille d’écran (Priorité : P3)

En tant qu’utilisateur sur ordinateur ou mobile, je veux que le formulaire reste confortable et entièrement accessible quelle que soit la taille de la fenêtre.

**Pourquoi cette priorité** : l’interface client doit rester simple dans tous les contextes courants.

**Test indépendant** : ouvrir la page sur une petite largeur mobile et sur un grand écran, puis parcourir l’ensemble du formulaire.

**Scénarios d’acceptation** :

1. **Étant donné** une fenêtre étroite, **quand** la page est affichée, **alors** aucun contenu utile n’est coupé et aucun défilement horizontal n’apparaît.

### Cas limites

- Les textes français longs ne doivent pas déborder de la carte.
- L’icône d’affichage du mot de passe doit rester visible sans recouvrir le texte saisi.
- Les erreurs, les chargements et les boutons désactivés doivent rester compréhensibles.
- Les modes inscription, connexion et LDAP doivent conserver la même hiérarchie visuelle.
- Le formulaire doit rester accessible lorsque sa hauteur dépasse celle d’un petit écran.
- Lors de la première utilisation, l’écran de bienvenue et le formulaire de création du compte administrateur ne doivent jamais se superposer.

## Exigences

### Exigences fonctionnelles

- **FR-001** : Chaque champ d’authentification DOIT posséder une limite visuelle et une surface distincte de l’arrière-plan.
- **FR-002** : Les libellés, valeurs et placeholders DOIVENT rester lisibles en thème sombre et clair, avec les placeholders visuellement secondaires.
- **FR-003** : Les champs DOIVENT présenter des espacements internes et verticaux cohérents.
- **FR-004** : Le champ actif DOIT posséder un indicateur de focus clairement visible.
- **FR-005** : L’action principale DOIT être visuellement prioritaire et présenter des états de survol, focus et désactivation.
- **FR-006** : Le formulaire DOIT être regroupé dans une zone visuelle clairement délimitée.
- **FR-007** : Tous les modes et comportements d’authentification existants DOIVENT être préservés.
- **FR-008** : La page DOIT rester utilisable sans défilement horizontal sur les tailles d’écran courantes.
- **FR-009** : Les libellés français et les attributs d’accessibilité existants DOIVENT être préservés.
- **FR-010** : Lors de la première utilisation, le système DOIT afficher l’écran de bienvenue seul, puis le formulaire de création du compte administrateur après l’action « Démarrer ».

## Critères de réussite

### Résultats mesurables

- **SC-001** : Un nouvel utilisateur peut identifier les champs requis et l’action principale en moins de cinq secondes.
- **SC-002** : Tous les champs et boutons principaux disposent d’un contraste lisible au repos et au focus dans les thèmes sombre et clair.
- **SC-003** : Les parcours inscription, connexion et LDAP restent réalisables sans régression fonctionnelle.
- **SC-004** : La page reste exploitable à partir d’une largeur de 320 pixels sans défilement horizontal.
- **SC-005** : Un nouvel utilisateur accède au formulaire contenant le nom, le courriel et le mot de passe après une seule action sur « Démarrer », sans rencontrer de formulaire de connexion ni d’erreur 401.

## Hypothèses

- Le système d’authentification, les appels réseau et la validation restent inchangés.
- Cette étape porte uniquement sur la présentation et la lisibilité de la page d’authentification.
- Le contenu, le logo et la structure des différents modes existants sont conservés.
- Les thèmes sombre et clair ainsi que les écrans mobiles et bureau sont inclus.
