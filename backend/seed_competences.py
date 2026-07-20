#!/usr/bin/env python3
"""Compétences métier livrées avec LunarIA (SPEC-competences-livrees.md).

Le client n'ouvre jamais un écran vide : à l'installation, l'onglet Compétences
contient déjà des savoir-faire qu'un dirigeant reconnaît, rangés par métier.

IDEMPOTENT et NON DESTRUCTIF : une compétence déjà présente n'est JAMAIS écrasée.
Si le patron modifie « Première relance d'impayé », sa version survit à tous les
redémarrages et à toutes les mises à jour. On ne recrée que ce qui manque.

Les dates et obligations citées sont vérifiées à la source (voir la spec) — jamais
inventées. Quand un fait dépend de la situation du client, la compétence dit
comment le vérifier au lieu d'affirmer.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from open_webui.hermes_bridge import skills_adapter  # noqa: E402

# --- Le catalogue livré -------------------------------------------------------
# (libellé, catégorie, description courte, procédure)
# La description dit CE QUE FAIT la compétence ET QUAND l'utiliser : c'est elle
# qui permet à un agent de la déclencher au bon moment.

COMPETENCES: list[tuple[str, str, str, str]] = [
    # ---------------------------------------------------------------- Finance
    (
        "Première relance d'impayé",
        "Finance & Compta",
        "Rédige une première relance courtoise pour une facture échue. À utiliser dès qu'une facture dépasse sa date d'échéance, avant toute mesure plus ferme.",
        """## Quand l'utiliser

Une facture a dépassé sa date d'échéance de quelques jours. C'est le premier contact : on part du principe que c'est un oubli.

## Ce qu'il faut avant d'écrire

- Le nom du client et son interlocuteur habituel
- Le numéro de facture, son montant TTC, sa date d'émission et sa date d'échéance
- L'historique de paiement de ce client (bon payeur ou retards répétés ?)

Si une de ces informations manque, demande-la — n'invente jamais un montant ou une référence.

## La procédure

1. **Ton courtois, jamais accusateur.** À ce stade, l'hypothèse de travail est l'oubli administratif.
2. **Rappelle les faits précis** : numéro de facture, montant, date d'échéance dépassée.
3. **Facilite le paiement** : rappelle les coordonnées bancaires et propose de renvoyer la facture si elle s'est perdue.
4. **Fixe une échéance courte et claire** (sous 8 jours), sans menace.
5. **Ouvre la porte** : « si un point bloque, dis-le nous, on trouvera une solution ».

## Le résultat attendu

Un email court (10 lignes maximum), objet explicite avec le numéro de facture, prêt à être relu et validé par le dirigeant. **Il ne part jamais sans sa validation.**

## Ce qu'il ne faut pas faire

- Menacer de pénalités dès la première relance
- Écrire un pavé : plus c'est long, moins c'est lu
- Relancer sans avoir vérifié que le paiement n'est pas déjà arrivé""",
    ),
    (
        "Deuxième relance d'impayé",
        "Finance & Compta",
        "Rédige une relance ferme mais professionnelle quand la première est restée sans réponse. À utiliser environ 15 jours après la première relance.",
        """## Quand l'utiliser

La première relance est restée sans réponse ni paiement, environ 15 jours plus tard.

## Ce qu'il faut avant d'écrire

- Tout ce qu'il fallait pour la première relance
- La date d'envoi de la première relance et son contenu
- Confirmation que le paiement n'est toujours pas arrivé

## La procédure

1. **Rappelle la première relance** avec sa date : cela montre le suivi et pose le sérieux.
2. **Reste professionnel, monte d'un cran.** Fermeté ≠ agressivité : le client reste un client.
3. **Rappelle le montant et le retard en jours**, chiffres exacts.
4. **Mentionne les pénalités de retard** SI et seulement SI elles figurent sur les conditions générales de vente de l'entreprise. Si tu ne peux pas le vérifier, ne les invente pas : demande au dirigeant.
5. **Demande un engagement daté** : soit le paiement, soit une date de paiement annoncée.
6. **Propose l'échéancier** si le client est habituellement fiable — mieux vaut un paiement étalé qu'un contentieux.

## Le résultat attendu

Un email ferme et factuel, prêt à validation. Après cet envoi, prépare le dirigeant à la suite : mise en demeure si toujours rien.

## Ce qu'il ne faut pas faire

- Passer directement au ton juridique : c'est l'étape d'après
- Inventer un taux de pénalité
- Oublier de vérifier que le paiement n'est pas arrivé entre-temps""",
    ),
    (
        "Mise en demeure de payer",
        "Finance & Compta",
        "Prépare le courrier de mise en demeure, dernière étape amiable avant procédure. À utiliser après deux relances restées sans effet.",
        """## Quand l'utiliser

Deux relances sont restées sans effet. C'est la dernière étape amiable : le courrier a une portée juridique, il marque le point de départ de la procédure.

## Avertissement à donner au dirigeant

Cette étape engage. Elle abîme souvent la relation commerciale — il faut que le dirigeant le décide en connaissance de cause. **Ce courrier ne part jamais sans sa validation explicite.** Et pour tout ce qui touche au droit, la compétence ne remplace pas un avocat ou un huissier : elle prépare, elle ne conseille pas juridiquement.

## Ce qu'il faut avant d'écrire

- La facture, son montant, sa date d'échéance
- Les dates et contenus des deux relances précédentes
- Les conditions générales de vente de l'entreprise (pour les pénalités)

## La procédure

1. **Titre explicite** : « Mise en demeure de payer » — l'intitulé compte juridiquement.
2. **Rappel chronologique factuel** : facture, échéance, relance 1, relance 2, avec les dates.
3. **Montant exact réclamé**, principal et pénalités si elles sont prévues aux conditions générales.
4. **Délai impératif** : 8 à 15 jours, date précise indiquée.
5. **Conséquence annoncée** en cas de silence, sans exagérer ni bluffer.
6. **Recommande l'envoi en recommandé avec accusé de réception** : sans preuve de réception, la mise en demeure perd son intérêt.

## Le résultat attendu

Un courrier prêt à imprimer et à envoyer en recommandé, plus un rappel au dirigeant : conserver l'accusé de réception.""",
    ),
    (
        "Échéancier de paiement",
        "Finance & Compta",
        "Construit une proposition de paiement échelonné pour un client en difficulté. À utiliser quand le client est de bonne foi mais ne peut pas payer en une fois.",
        """## Quand l'utiliser

Un client reconnaît sa dette mais ne peut pas payer en une seule fois. Mieux vaut un paiement étalé et tenu qu'un contentieux long et coûteux.

## La procédure

1. **Vérifie l'historique** : ce client a-t-il déjà tenu ses engagements ? Un mauvais payeur chronique ne mérite pas les mêmes facilités.
2. **Propose un échéancier réaliste** : un premier versement immédiat significatif, puis des mensualités sur une durée courte.
3. **Écris chaque échéance** : date exacte et montant exact, pas d'approximation.
4. **Mentionne la clause de déchéance du terme** : une échéance manquée rend la totalité exigible. C'est ce qui protège l'entreprise.
5. **Fais signer** : un échéancier accepté par écrit vaut engagement.

## Le résultat attendu

Un document clair avec le tableau des échéances, prêt à être envoyé au client pour signature, après validation du dirigeant.

## Ce qu'il ne faut pas faire

- Accorder un étalement sans premier versement
- Étaler sur une durée trop longue : le risque augmente avec le temps
- Oublier la clause de déchéance du terme""",
    ),
    (
        "Facturation électronique 2026",
        "Finance & Compta",
        "Explique la réforme de la facturation électronique et prépare l'entreprise à ses échéances. À utiliser quand le dirigeant s'interroge sur ce qu'il doit faire et quand.",
        """## Ce que dit la réforme

Deux dates structurent l'obligation, et elles ne dépendent pas du même critère :

- **1er septembre 2026** : TOUTES les entreprises assujetties à la TVA doivent être **capables de RECEVOIR** une facture électronique. Aucune exception de taille. À la même date, les grandes entreprises et les ETI doivent aussi **émettre** en électronique.
- **1er septembre 2027** : les TPE et PME doivent à leur tour **émettre** leurs factures en électronique.

Autrement dit, pour une PME : **recevoir dès septembre 2026, émettre à partir de septembre 2027**.

## Les nouvelles mentions obligatoires

À compter du 1er septembre 2026, des mentions supplémentaires s'ajoutent aux factures, notamment :

- la catégorie de l'opération (vente de biens, prestation de services, ou les deux)
- l'option de paiement de la TVA sur les débits, le cas échéant
- l'adresse de livraison du bien lorsqu'elle diffère de l'adresse de facturation

## La procédure d'accompagnement

1. **Situe l'entreprise** : sa taille détermine sa date d'obligation d'émission. Demande l'effectif et le chiffre d'affaires si tu ne les connais pas.
2. **Vérifie la capacité de réception** : c'est l'échéance la plus proche et elle concerne tout le monde.
3. **Recense les outils actuels** : logiciel de facturation, expert-comptable, plateforme envisagée.
4. **Établis un calendrier de préparation** en remontant depuis la date d'obligation.
5. **Renvoie vers l'expert-comptable** pour le choix de la plateforme et le paramétrage fiscal : ce n'est pas du conseil que tu donnes.

## Règle de prudence

Les modalités de cette réforme ont déjà été reportées par le passé. Avant d'affirmer une date à un client, **vérifie qu'elle est toujours d'actualité** sur le site officiel de l'administration fiscale. Si tu ne peux pas vérifier, dis-le.""",
    ),
    # ---------------------------------------------------------------- Juridique
    (
        "Registre RGPD des traitements",
        "Juridique",
        "Aide à construire et tenir le registre des activités de traitement de données personnelles. À utiliser quand le dirigeant doit se mettre en conformité ou préparer un contrôle.",
        """## Ce qu'est ce registre

Le registre des activités de traitement recense ce que l'entreprise fait des données personnelles qu'elle détient : clients, salariés, prospects, fournisseurs. C'est le document de base de la conformité RGPD, et le premier demandé en cas de contrôle.

## Ce qu'on inscrit pour chaque traitement

1. **Le nom du traitement** : « gestion de la paie », « fichier clients », « campagnes email ».
2. **La finalité** : à quoi ça sert, concrètement.
3. **Les catégories de personnes** concernées : clients, salariés, candidats…
4. **Les catégories de données** : identité, coordonnées, données bancaires, données de santé…
5. **Qui y a accès**, en interne et à l'extérieur (prestataires, logiciels).
6. **La durée de conservation** : combien de temps on garde, et pourquoi.
7. **Les mesures de sécurité** : mots de passe, accès restreints, chiffrement, sauvegardes.

## La procédure

1. **Fais l'inventaire par service** : commercial, comptabilité, RH, production. Le tour du propriétaire vaut mieux que la théorie.
2. **N'oublie pas les logiciels** : chaque outil qui stocke des données est un traitement (CRM, paie, caisse, réservation).
3. **Attention aux données sensibles** (santé, opinions, biométrie) : elles obéissent à des règles plus strictes.
4. **Date le registre** et prévois sa mise à jour à chaque nouveau traitement.

## Point de vigilance

Certaines situations imposent des obligations supplémentaires, comme la désignation d'un délégué à la protection des données ou la réalisation d'une analyse d'impact. Ces cas dépendent de l'activité — **renvoie vers la CNIL ou un juriste plutôt que de trancher toi-même**.""",
    ),
    (
        "Dépôt des comptes annuels",
        "Juridique",
        "Guide le dirigeant de société dans l'approbation et le dépôt de ses comptes annuels. À utiliser à l'approche de la clôture d'exercice.",
        """## Ce que l'obligation recouvre

Une société commerciale doit faire approuver ses comptes annuels par ses associés, puis les déposer au greffe du tribunal de commerce. Deux étapes distinctes, avec deux délais.

## La procédure

1. **Repère la date de clôture** de l'exercice — c'est elle qui déclenche tous les délais.
2. **Fais préparer les comptes** par l'expert-comptable : bilan, compte de résultat, annexe.
3. **Organise l'approbation** par l'assemblée des associés, et fais rédiger le procès-verbal.
4. **Décide de l'affectation du résultat** : mise en réserve, report, distribution de dividendes.
5. **Dépose au greffe** dans le délai imparti après l'approbation.
6. **Vérifie la confidentialité** : selon la taille de la société, certains documents peuvent être déposés sans être rendus publics. Vérifie l'éligibilité de l'entreprise.

## Règle de prudence

Les délais exacts et les seuils de confidentialité dépendent de la forme juridique et de la taille de la société, et ils évoluent. **Ne les affirme jamais de mémoire** : fais-les confirmer par l'expert-comptable ou vérifie-les sur le site officiel avant de donner une date au dirigeant.

## Ce qui se passe en cas de retard

Le retard expose à des sanctions et peut être relevé par des tiers. Si l'échéance est proche ou dépassée, alerte le dirigeant immédiatement plutôt que d'attendre.""",
    ),
    (
        "Relecture d'un contrat fournisseur",
        "Juridique",
        "Passe en revue un contrat fournisseur et signale les points d'attention avant signature. À utiliser avant tout engagement avec un nouveau prestataire.",
        """## Ce que fait cette compétence, et ce qu'elle ne fait pas

Elle **prépare la lecture** d'un contrat en signalant les clauses qui méritent l'attention du dirigeant. Elle **ne donne pas de conseil juridique** et ne remplace pas un avocat sur un engagement important.

## Les points à examiner systématiquement

1. **La durée et la reconduction** : le contrat se renouvelle-t-il tout seul ? Souvent la mauvaise surprise vient de là.
2. **Le préavis de résiliation** : combien de temps avant l'échéance faut-il prévenir, et par quel moyen ?
3. **Le prix et sa révision** : le tarif peut-il augmenter en cours de contrat, selon quel indice, avec quel plafond ?
4. **Les engagements de volume** : y a-t-il un minimum à commander, avec quelle pénalité ?
5. **Les délais de paiement** et les pénalités de retard.
6. **Les responsabilités** : que se passe-t-il en cas de défaillance du fournisseur ? Y a-t-il un plafond d'indemnisation ?
7. **La propriété** de ce qui est produit ou des données confiées.

## Le résultat attendu

Une note courte pour le dirigeant : les 3 à 5 points qui méritent une négociation ou une question au fournisseur, en français simple, avec pour chacun le risque concret.

## Signal d'alerte

Si le contrat comporte un engagement long avec reconduction automatique et préavis long, **dis-le en premier** : c'est le piège le plus fréquent et le plus coûteux.""",
    ),
    # ---------------------------------------------------------------- Vente
    (
        "Fiche de préparation d'appel",
        "Vente",
        "Prépare une fiche synthétique avant un rendez-vous ou un appel commercial. À utiliser avant chaque premier contact avec un prospect.",
        """## Quand l'utiliser

Avant un premier appel ou un rendez-vous avec un prospect. L'objectif : arriver en sachant à qui on parle, pour ne pas poser de questions dont la réponse est publique.

## Ce qu'on rassemble

1. **L'identité de l'entreprise** : dénomination, forme juridique, année de création, effectif, adresse du siège.
2. **Son activité réelle** : ce qu'elle fait vraiment, pas seulement son code d'activité.
3. **Ses dirigeants** : qui décide, depuis quand.
4. **Sa santé apparente** : croissance, ouvertures, recrutements, difficultés visibles.
5. **Son actualité récente** : ce qui a bougé ces derniers mois.
6. **Le point d'accroche** : la raison concrète de l'appeler maintenant.

## La procédure

1. **Pars des sources officielles** pour l'identité et les chiffres — jamais de la mémoire.
2. **Complète par le site de l'entreprise** et son actualité publique.
3. **Distingue ce qui est vérifié de ce qui est supposé.** Tout élément non confirmé est marqué « à vérifier ».
4. **Termine par trois questions à poser** pendant l'appel, qui montrent que le travail a été fait.

## Le résultat attendu

Une fiche d'une page, lisible en deux minutes juste avant l'appel.

## Règle absolue

**Zéro invention.** Un chiffre d'affaires estimé, un effectif approximatif ou un nom de dirigeant supposé décrédibilisent tout l'appel. Quand l'information manque, on écrit qu'elle manque.""",
    ),
    (
        "Qualification d'un prospect",
        "Vente",
        "Évalue si un prospect mérite qu'on investisse du temps, et pourquoi. À utiliser après un premier contact, avant d'engager un travail commercial.",
        """## Quand l'utiliser

Après un premier échange, pour décider si on poursuit ou si on laisse tomber. Le temps commercial est la ressource la plus rare d'une PME.

## Les critères à évaluer

1. **Le besoin est-il réel et exprimé ?** Un besoin qu'on a deviné n'est pas un besoin.
2. **Y a-t-il un budget ?** Ou au moins la capacité d'en dégager un.
3. **Parle-t-on au décideur ?** Sinon, qui décide et comment l'atteindre.
4. **Y a-t-il une échéance ?** Un projet sans date est un projet qui n'existe pas.
5. **Est-on dans la cible ?** Taille, secteur, zone géographique.

## La procédure

1. **Note chaque critère** avec ce qui est su et ce qui manque.
2. **Classe le prospect** : chaud (besoin, budget et échéance confirmés), tiède (besoin réel mais un élément manque), froid (à recontacter plus tard).
3. **Justifie le classement en une phrase.** Un classement sans justification ne sert à rien.
4. **Propose la prochaine action** et sa date.

## Le résultat attendu

Un verdict clair avec sa raison, et une action datée. Pas de « à suivre » vague.

## Règle

On ne gonfle jamais un classement pour faire plaisir. Un prospect froid annoncé comme chaud fait perdre plus de temps qu'il n'en fait gagner.""",
    ),
    # ---------------------------------------------------------------- Achats
    (
        "Bon de commande fournisseur",
        "Achats",
        "Prépare un bon de commande clair à partir d'un besoin exprimé. À utiliser dès qu'une commande fournisseur doit être passée par écrit.",
        """## Ce qu'un bon de commande doit contenir

1. **Un numéro unique** et la date d'émission.
2. **L'identité complète** de l'entreprise et du fournisseur.
3. **Le détail des articles** : référence, désignation précise, quantité, prix unitaire hors taxes, total.
4. **Les conditions financières** : total hors taxes, TVA applicable, total toutes taxes comprises.
5. **La date de livraison souhaitée** et le lieu exact.
6. **Les conditions de paiement** convenues.
7. **La référence à l'offre du fournisseur** si la commande fait suite à un devis.

## La procédure

1. **Vérifie chaque prix** contre le devis ou le tarif négocié. Un écart de prix repéré à la commande coûte dix fois moins cher qu'un écart repéré à la facture.
2. **Sois précis sur les désignations** : « 20 cartons » ne veut rien dire, « 20 cartons de 12 bouteilles, référence X » se contrôle à la réception.
3. **Fixe une date de livraison réaliste** et note-la pour le suivi.
4. **Fais valider** avant envoi : un bon de commande engage l'entreprise.

## Le résultat attendu

Un document prêt à envoyer, et une entrée dans le suivi des commandes pour contrôler la livraison le moment venu.

## Ce qu'il ne faut pas faire

- Commander sans référence ni prix : le litige est garanti
- Inventer un prix « à peu près » — demande-le si tu ne l'as pas""",
    ),
    (
        "Comparaison de devis fournisseurs",
        "Achats",
        "Compare plusieurs devis sur une grille objective pour éclairer une décision d'achat. À utiliser dès qu'au moins deux offres sont sur la table.",
        """## Pourquoi une grille

Comparer deux devis « au feeling » revient presque toujours à choisir le moins cher, qui n'est presque jamais le meilleur. La grille rend la décision explicite.

## Les critères de comparaison

1. **Le prix total réel** : hors taxes et toutes taxes comprises, options et frais de livraison inclus. C'est là que les écarts se cachent.
2. **Ce qui est réellement inclus** : garantie, installation, formation, maintenance, support.
3. **Le délai de livraison** et sa fermeté.
4. **Les conditions de paiement** : un délai plus long a une valeur pour la trésorerie.
5. **La solidité du fournisseur** : ancienneté, références, situation apparente.
6. **Les conditions de sortie** : durée d'engagement, préavis.

## La procédure

1. **Ramène toutes les offres au même périmètre.** Si l'une inclut l'installation et l'autre non, ajoute le coût manquant avant de comparer.
2. **Établis le tableau** critère par critère.
3. **Signale les écarts marquants** en une phrase chacun.
4. **Donne une recommandation motivée** — pas seulement un tableau. Le dirigeant attend un avis.

## Le résultat attendu

Un tableau comparatif et une recommandation en trois lignes : lequel, pourquoi, et à quelle condition.

## Point de vigilance

Un prix nettement inférieur aux autres cache généralement quelque chose : périmètre réduit, qualité moindre, ou offre d'appel avec reconduction coûteuse. **Signale-le au lieu de conclure au bon plan.**""",
    ),
    (
        "Suivi des contrats fournisseurs",
        "Achats",
        "Tient à jour les échéances des contrats fournisseurs et alerte avant les dates critiques. À utiliser pour éviter les reconductions automatiques subies.",
        """## Le problème que ça résout

Un contrat qui se reconduit tout seul parce que le préavis a été oublié, c'est un an de plus à un tarif qu'on ne voulait plus. C'est l'une des fuites d'argent les plus fréquentes et les plus évitables en PME.

## Ce qu'on suit pour chaque contrat

1. **Le fournisseur** et l'objet du contrat.
2. **La date de début** et la durée d'engagement.
3. **La date d'échéance**.
4. **La durée du préavis** de résiliation.
5. **La date limite pour dénoncer** — calculée en remontant depuis l'échéance. C'est LA date qui compte.
6. **Le montant annuel** et les modalités de révision de prix.
7. **Le mode de dénonciation** exigé (recommandé, formulaire, espace en ligne).

## La procédure

1. **Recense tous les contrats récurrents** : télécoms, logiciels, assurances, maintenance, énergie, location.
2. **Calcule pour chacun la date limite de dénonciation.**
3. **Pose une alerte un mois avant cette date limite** — pas avant l'échéance, avant la date limite de préavis.
4. **À chaque alerte, pose la question au dirigeant** : on garde, on renégocie, ou on arrête ?

## Le résultat attendu

Un tableau de suivi et des alertes posées aux bonnes dates.

## Point de vigilance restauration multi-établissements

Les contrats sont souvent signés établissement par établissement, avec des dates différentes. **Suis-les séparément** : une échéance groupée est une hypothèse, pas une réalité.""",
    ),
    # ---------------------------------------------------------------- Service client
    (
        "Réponse à une réclamation client",
        "Service client",
        "Prépare une réponse à un client mécontent, qui traite le problème sans envenimer la relation. À utiliser dès qu'une réclamation écrite arrive.",
        """## Quand l'utiliser

Un client exprime un mécontentement par écrit. Le premier réflexe compte : une réclamation bien traitée fidélise souvent plus qu'une commande sans accroc.

## La procédure

1. **Accuse réception vite**, même sans solution immédiate. Le silence transforme l'agacement en colère.
2. **Reformule le problème** avec les mots du client : il doit se sentir compris avant d'être satisfait.
3. **Établis les faits** : commande, date, ce qui était prévu, ce qui s'est passé. Sans les faits, on négocie dans le vide.
4. **Reconnais ce qui est réellement de la responsabilité de l'entreprise** — ni plus, ni moins. Ne t'excuse pas de ce qui n'est pas ta faute, n'esquive pas ce qui l'est.
5. **Propose une solution concrète et datée** : remplacement, avoir, geste commercial, intervention.
6. **Termine sur l'ouverture** : ce qui sera fait pour que ça ne se reproduise pas.

## Le résultat attendu

Un email court, factuel, avec une solution et une date, prêt à validation du dirigeant.

## Ce qu'il ne faut pas faire

- Se justifier longuement : le client veut une solution, pas une explication interne
- Promettre un geste commercial sans l'accord du dirigeant — **tout geste financier passe par lui**
- Répondre à chaud sur le même ton""",
    ),
    # ---------------------------------------------------------------- Pilotage
    (
        "Point de trésorerie hebdomadaire",
        "Pilotage",
        "Construit le point de trésorerie de la semaine : ce qui rentre, ce qui sort, ce qui inquiète. À utiliser en début de semaine pour piloter.",
        """## Ce que le dirigeant veut savoir en deux minutes

Combien j'ai, combien je vais encaisser, combien je dois sortir, et qu'est-ce qui menace.

## La structure du point

1. **La position actuelle** : solde disponible à date.
2. **Les encaissements attendus cette semaine** : montants et probabilité réelle (une facture échue depuis 60 jours n'est pas un encaissement « attendu »).
3. **Les décaissements prévus** : salaires, charges, fournisseurs, échéances.
4. **Le solde projeté** en fin de semaine.
5. **Les points d'attention** : impayés qui traînent, échéance importante, client en difficulté.

## La procédure

1. **Pars des chiffres réels**, jamais d'estimations. Si une donnée manque, dis-le : un point de trésorerie faux est pire que pas de point du tout.
2. **Distingue le certain du probable.** Un encaissement promis n'est pas un encaissement reçu.
3. **Signale les impayés** avec leur ancienneté — ils font le lien avec les relances.
4. **Termine par la question la plus utile du moment**, pas par un résumé.

## Le résultat attendu

Un point en cinq lignes maximum, lisible d'un coup d'œil, avec les montants exacts.

## Règle absolue

**Aucun chiffre inventé, aucune estimation présentée comme un fait.** La trésorerie est le sujet où une approximation coûte le plus cher.""",
    ),
    # ---------------------------------------------------------------- Process & SOP
    (
        "Rédiger une procédure interne",
        "Process & SOP",
        "Transforme une façon de faire en procédure écrite, transmissible à un nouveau salarié. À utiliser quand un savoir-faire ne vit que dans la tête d'une personne.",
        """## Le problème que ça résout

Dans une PME, beaucoup de savoir-faire ne sont écrits nulle part. Quand la personne qui sait est absente ou part, tout se bloque. Écrire la procédure, c'est transformer un savoir personnel en actif de l'entreprise.

## La structure d'une bonne procédure

1. **Le titre** : ce que la procédure permet de faire.
2. **Quand elle s'applique** — et quand elle ne s'applique pas.
3. **Ce qu'il faut avant de commencer** : accès, documents, informations.
4. **Les étapes numérotées**, dans l'ordre, une action par étape.
5. **Les points de vigilance** : les erreurs classiques, les cas particuliers.
6. **Qui contacter** en cas de blocage.

## La procédure pour écrire une procédure

1. **Fais raconter le déroulé** par la personne qui fait le travail, dans ses mots.
2. **Écris chaque étape comme une action** : « ouvrir X », « vérifier que Y », pas « gestion de Z ».
3. **Teste la lisibilité** : quelqu'un qui ne connaît pas le sujet doit pouvoir suivre sans poser de question.
4. **Note les cas particuliers** séparément, pour ne pas alourdir le déroulé principal.
5. **Date la procédure** et prévois qui la met à jour.

## Le résultat attendu

Un document qu'un nouveau salarié peut suivre seul dès son premier jour.

## Ce qu'il ne faut pas faire

- Écrire au conditionnel ou dans le vague
- Sauter les étapes « évidentes » : elles ne le sont que pour celui qui sait déjà""",
    ),
]


def main() -> int:
    existantes = {s.name for s in skills_adapter.list_custom_skills()}
    creees = 0
    ignorees = 0

    for label, categorie, description, procedure in COMPETENCES:
        res = skills_adapter.create_custom_skill(
            label=label, description=description, instructions=procedure, category=categorie
        )
        if res.get("ok"):
            creees += 1
        else:
            # « exists » : la compétence est déjà là (livrée précédemment ou modifiée par
            # le patron). On ne la touche JAMAIS — sa version prime toujours sur la nôtre.
            ignorees += 1

    print(
        f"Compétences livrées : {creees} créée(s), {ignorees} déjà présente(s) et conservée(s) "
        f"(sur {len(COMPETENCES)} au catalogue ; {len(existantes)} compétence(s) avant ce passage)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
