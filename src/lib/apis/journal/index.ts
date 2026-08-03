/**
 * Le registre des traitements, vu depuis le navigateur.
 *
 * Comme pour le kanban : aucune adresse de moteur ici. Ces routes sont servies
 * par Open WebUI lui-meme, qui detient le journal — le moteur, lui, ne sait pas
 * dire ce qu'il a fait.
 *
 * Les erreurs remontent avec leur code HTTP intact, pour que `lib/journal/
 * synthese.ts` puisse distinguer un journal vide (rien a montrer, tout va bien)
 * d'un serveur qui ne repond pas (etat inconnu, surtout pas une panne).
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';

export type StatutTraitement = 'ok' | 'pending' | 'error' | 'unknown';
export type SourceTraitement = 'interface' | 'telegram' | 'scheduled' | 'api';

export type Traitement = {
	id: string;
	user_id?: string | null;
	source: SourceTraitement;
	action: string;
	status: StatutTraitement;
	summary?: string | null;
	reference?: string | null;
	error?: string | null;
	meta?: Record<string, unknown> | null;
	created_at: number;
};

export type CompteursTraitements = {
	ok: number;
	pending: number;
	error: number;
	unknown: number;
	total: number;
};

export type SyntheseJournal = {
	fenetre: string;
	compteurs: CompteursTraitements;
	dernieres: Traitement[];
};

export type Fenetre = 'jour' | 'semaine' | 'mois' | 'tout';

class ErreurJournal extends Error {
	statut: number;

	constructor(statut: number, message: string) {
		super(message);
		this.name = 'ErreurJournal';
		this.statut = statut;
	}
}

const appeler = async <T>(token: string, chemin: string): Promise<T> => {
	let reponse: Response;

	try {
		reponse = await fetch(`${WEBUI_API_BASE_URL}/journal${chemin}`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		});
	} catch (erreur) {
		// Le serveur n'a pas repondu du tout. 0 n'est pas un code HTTP : il dit
		// « on ne sait pas », ce qui n'est pas la meme chose qu'une panne.
		throw new ErreurJournal(0, `${erreur}`);
	}

	if (!reponse.ok) {
		let detail = reponse.statusText;
		try {
			const corps = await reponse.json();
			detail = corps?.detail ?? detail;
		} catch {
			// Corps illisible : le code HTTP suffit a decider quoi afficher.
		}
		throw new ErreurJournal(reponse.status, detail);
	}

	return reponse.json();
};

export const getSyntheseJournal = (token: string, fenetre: Fenetre = 'jour', apercu = 10) =>
	appeler<SyntheseJournal>(
		token,
		`/synthese?fenetre=${encodeURIComponent(fenetre)}&apercu=${apercu}`
	);

export const getTraitements = (
	token: string,
	options: { limit?: number; skip?: number; statut?: StatutTraitement; fenetre?: Fenetre } = {}
) => {
	const parametres = new URLSearchParams();
	if (options.limit !== undefined) parametres.set('limit', `${options.limit}`);
	if (options.skip !== undefined) parametres.set('skip', `${options.skip}`);
	if (options.statut !== undefined) parametres.set('statut', options.statut);
	if (options.fenetre !== undefined) parametres.set('fenetre', options.fenetre);

	const requete = parametres.toString();
	return appeler<Traitement[]>(token, requete ? `/?${requete}` : '/');
};

export const getTraitement = (token: string, id: string) =>
	appeler<Traitement>(token, `/${encodeURIComponent(id)}`);

/**
 * Signe ou refuse un dossier prepare.
 *
 * Le 409 n'est pas une panne : il dit que quelqu'un d'autre a signe entre-temps.
 * L'interface doit rafraichir, pas afficher une erreur rouge — c'est le cas
 * courant quand deux personnes regardent la meme file.
 */
export const deciderTraitement = async (
	token: string,
	id: string,
	issue: 'ok' | 'error',
	motif?: string
): Promise<Traitement> => {
	let reponse: Response;

	try {
		reponse = await fetch(`${WEBUI_API_BASE_URL}/journal/${encodeURIComponent(id)}/decision`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ issue, motif })
		});
	} catch (erreur) {
		throw new ErreurJournal(0, `${erreur}`);
	}

	if (!reponse.ok) {
		let detail = reponse.statusText;
		try {
			const corps = await reponse.json();
			detail = corps?.detail ?? detail;
		} catch {
			// Le code HTTP suffit.
		}
		throw new ErreurJournal(reponse.status, detail);
	}

	return reponse.json();
};
