/**
 * Ce que l'ecran d'accueil a le droit d'affirmer sur la journee.
 *
 * Meme regle que partout ailleurs (D27, heritee d'AgentOS V1) : un etat inconnu
 * n'est jamais presente comme une panne. Elle se decline ici en trois pieges
 * concrets, qui sont les trois raisons d'etre de ce fichier :
 *
 *   1. **Journal vide n'est pas panne.** Aucun traitement enregistre veut dire
 *      « rien ne s'est passe », pas « tout a echoue ». Un matin sans commande
 *      est un matin normal.
 *
 *   2. **`unknown` n'est pas `error`.** Le moteur injoignable au moment ou il
 *      rendait compte ne dit rien sur le traitement lui-meme, qui a pu tres
 *      bien aboutir. Le compter comme un echec ferait afficher une panne a
 *      quelqu'un dont tout va bien.
 *
 *   3. **`pending` n'est pas un probleme, c'est le produit.** Ce sont les
 *      dossiers prepares qui attendent une signature. Les afficher en rouge a
 *      cote des erreurs ferait passer le fonctionnement normal pour une avarie.
 */

export type StatutTraitement = 'ok' | 'pending' | 'error' | 'unknown';

export type Compteurs = {
	ok: number;
	pending: number;
	error: number;
	unknown: number;
	total: number;
};

/** Ce qu'une tuile doit exprimer visuellement. Jamais deduit d'un nombre seul. */
export type Ton = 'neutre' | 'positif' | 'attention' | 'probleme';

export type Tuile = {
	statut: StatutTraitement;
	valeur: number;
	ton: Ton;
};

export type Gravite = 'information' | 'avertissement';

export type Alerte = {
	gravite: Gravite;
	cle: string;
};

export const COMPTEURS_VIDES: Compteurs = {
	ok: 0,
	pending: 0,
	error: 0,
	unknown: 0,
	total: 0
};

/**
 * Le ton d'une tuile.
 *
 * `pending` est en `attention` et non en `probleme` : il appelle un geste, il
 * ne signale pas une avarie. `unknown` reste `neutre` — on ne sait pas, et on
 * ne fait pas peur avec ce qu'on ignore.
 */
export const tonDeStatut = (statut: StatutTraitement, valeur: number): Ton => {
	if (valeur === 0) {
		return 'neutre';
	}

	switch (statut) {
		case 'ok':
			return 'positif';
		case 'pending':
			return 'attention';
		case 'error':
			return 'probleme';
		default:
			return 'neutre';
	}
};

/** Les quatre tuiles, dans l'ordre ou elles se lisent. */
export const tuiles = (compteurs: Compteurs): Tuile[] =>
	(['ok', 'pending', 'error', 'unknown'] as StatutTraitement[]).map((statut) => {
		const valeur = compteurs[statut] ?? 0;
		return { statut, valeur, ton: tonDeStatut(statut, valeur) };
	});

/**
 * L'alerte unique affichee en tete, ou rien.
 *
 * Une seule, jamais empilee : le corollaire de la regle D27. Les echecs reels
 * priment sur l'incertitude, qui prime sur l'attente.
 */
export const alerteJournal = (compteurs: Compteurs): Alerte | null => {
	if (compteurs.error > 0) {
		return { gravite: 'avertissement', cle: 'journal.alerte.erreurs' };
	}

	if (compteurs.unknown > 0) {
		return { gravite: 'information', cle: 'journal.alerte.inconnus' };
	}

	if (compteurs.pending > 0) {
		return { gravite: 'information', cle: 'journal.alerte.attente' };
	}

	return null;
};

/**
 * Distingue « rien a montrer » de « on n'a pas pu lire ».
 *
 * Sans cette distinction, une panne du journal afficherait une journee a zero
 * traitement, ce qui est un mensonge tranquille : l'ecran aurait l'air normal.
 */
export const etatAffichage = (
	compteurs: Compteurs | null,
	lectureEchouee: boolean
): 'donnees' | 'vide' | 'illisible' => {
	if (lectureEchouee) {
		return 'illisible';
	}

	if (compteurs === null) {
		return 'illisible';
	}

	return compteurs.total > 0 ? 'donnees' : 'vide';
};

/**
 * Part des traitements aboutis, sur ceux dont on connait l'issue.
 *
 * `unknown` est exclu du denominateur : on ne peut pas calculer un taux de
 * reussite sur des issues qu'on ignore. Rend `null` quand rien n'est connu,
 * plutot que 0 % — qui se lirait comme un echec total.
 */
export const tauxAboutis = (compteurs: Compteurs): number | null => {
	const connus = compteurs.ok + compteurs.pending + compteurs.error;
	if (connus === 0) {
		return null;
	}
	return Math.round(((compteurs.ok + compteurs.pending) / connus) * 100);
};
