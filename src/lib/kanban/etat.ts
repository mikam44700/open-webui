/**
 * Ce que la page a le droit d'affirmer sur le tableau.
 *
 * Reprise de la regle D27, heritee d'AgentOS V1 : un etat inconnu n'est jamais
 * presente comme une panne. Ici la regle se dedouble, parce qu'il y a deux
 * non-reponses de nature opposee :
 *
 *   - `absent`      le moteur repond, mais n'a pas de registre de taches. Ce
 *                   n'est pas une panne, c'est une fonction non installee. Ca
 *                   se regle par une installation, pas par une attente.
 *   - `injoignable` le moteur lui-meme ne repond pas. C'est temporaire, ca
 *                   revient, et il n'y a rien a faire.
 *
 * Les confondre ferait afficher « le moteur ne repond pas » a quelqu'un dont le
 * moteur va parfaitement bien.
 *
 * Et le corollaire, quand plusieurs sources dependent du meme pont coupe : une
 * seule alerte chapeau, jamais une pile d'« indisponible ».
 */

export type EtatLecture = 'ok' | 'absent' | 'injoignable' | 'inconnu';

export type Lecture<T = unknown> = { etat: EtatLecture; donnees?: T };

/**
 * Traduit l'echec d'un appel en etat de lecture.
 *
 * Le proxy traduit deja une injoignabilite reseau en 503 et un depassement de
 * delai en 504 (routers/hermes.py). Un 404 vient du plugin kanban absent cote
 * moteur. Tout le reste est `inconnu` : on ne conclut pas a partir d'un code
 * qu'on n'a pas prevu.
 */
export const lectureDepuisErreur = (erreur: unknown): Lecture => {
	const code =
		(erreur as { status?: number })?.status ??
		(erreur as { response?: { status?: number } })?.response?.status ??
		null;

	if (code === 404) return { etat: 'absent' };
	if (code === 503 || code === 504) return { etat: 'injoignable' };

	return { etat: 'inconnu' };
};

/**
 * L'etat d'ensemble, du plus precis au plus vague.
 *
 * `absent` prime : c'est la reponse la plus informative qu'on ait, et elle
 * explique tout le reste. Vient ensuite `injoignable`, qui est un fait sur le
 * moteur. `inconnu` ferme la marche : c'est un aveu, pas un diagnostic.
 */
export const etatDeLecture = (lectures: Lecture[]): EtatLecture => {
	if (lectures.some((l) => l.etat === 'absent')) return 'absent';
	if (lectures.some((l) => l.etat === 'injoignable')) return 'injoignable';
	if (lectures.some((l) => l.etat === 'inconnu')) return 'inconnu';

	return 'ok';
};

export type Gravite = 'information' | 'avertissement';

export type Alerte = {
	etat: Exclude<EtatLecture, 'ok'>;
	gravite: Gravite;
	/** Cle de traduction : le texte se resout dans le composant. */
	cleI18n: string;
};

const ALERTES: Record<Exclude<EtatLecture, 'ok'>, Alerte> = {
	absent: {
		etat: 'absent',
		// Une information, pas un avertissement : rien n'est casse, la fonction
		// n'est simplement pas installee sur ce moteur.
		gravite: 'information',
		cleI18n: 'Ce moteur n’a pas de registre de tâches installé.'
	},
	injoignable: {
		etat: 'injoignable',
		gravite: 'avertissement',
		cleI18n: 'Le moteur ne répond pas. Ce qui est affiché date de la dernière lecture.'
	},
	inconnu: {
		etat: 'inconnu',
		gravite: 'avertissement',
		cleI18n: 'Impossible de lire le tableau pour le moment.'
	}
};

/**
 * L'alerte a afficher en tete, ou `null` quand tout va bien.
 *
 * Une seule, quel que soit le nombre de sources tombees : c'est le meme pont qui
 * les porte, donc c'est un seul probleme.
 */
export const alerteChapeau = (lectures: Lecture[]): Alerte | null => {
	const etat = etatDeLecture(lectures);

	return etat === 'ok' ? null : ALERTES[etat];
};
