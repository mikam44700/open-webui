/**
 * Le tableau de taches, vu depuis le navigateur.
 *
 * Aucune adresse de moteur ici : tout passe par le proxy du backend, qui seul
 * detient l'URL et la cle. Les erreurs remontent avec leur code HTTP intact —
 * c'est lui qui permet a `lib/kanban/etat.ts` de distinguer un registre absent
 * (404) d'un moteur injoignable (503).
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';

export type TacheKanban = {
	id: string;
	titre: string;
	statut: string;
	typeBlocage?: string | null;
	responsable?: string | null;
	priorite?: number | null;
	creeLe?: number | null;
	demarreLe?: number | null;
	termineLe?: number | null;
	echecsConsecutifs?: number | null;
	reblocages?: number | null;
	nombreMessages?: number | null;
	/** Âge depuis la création. Le moteur le range dans un sous-objet, le proxy l'aplatit. */
	ageSecondes?: number | null;
};

/** Combien de parents et d'enfants une tâche porte, par identifiant de tâche. */
export type DependancesKanban = Record<
	string,
	{ parents: number; enfants: number; faits?: number | null; total?: number | null }
>;

export type MessageKanban = {
	auteur?: string | null;
	texte?: string | null;
	ecritLe?: number | null;
};

export type FicheKanban = TacheKanban & {
	consigne?: string | null;
	resultat?: string | null;
	derniereErreur?: string | null;
	messages: MessageKanban[];
};

export type ConfigKanban = { tableaux: string[]; tableauCourant: string | null };

const BASE = `${WEBUI_API_BASE_URL}/kanban`;

/**
 * Erreur portant le code HTTP.
 *
 * Une erreur nue perdrait le code, et la page ne saurait plus distinguer
 * « pas de registre » de « moteur coupe ».
 */
class ErreurKanban extends Error {
	status: number;

	constructor(status: number, message: string) {
		super(message);
		this.name = 'ErreurKanban';
		this.status = status;
	}
}

const appeler = async <T>(
	token: string,
	chemin: string,
	options: { methode?: string; corps?: unknown } = {}
): Promise<T> => {
	const reponse = await fetch(`${BASE}${chemin}`, {
		method: options.methode ?? 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		...(options.corps === undefined ? {} : { body: JSON.stringify(options.corps) })
	});

	if (!reponse.ok) {
		let detail = `Le tableau a répondu ${reponse.status}.`;
		try {
			const charge = await reponse.json();
			detail = charge?.detail ?? detail;
		} catch {
			// Une reponse sans corps lisible reste une erreur : c'est le code qui
			// compte, pas le texte.
		}
		throw new ErreurKanban(reponse.status, detail);
	}

	return reponse.json();
};

export const getConfigKanban = (token: string) => appeler<ConfigKanban>(token, '/config');

export const getTableauKanban = (
	token: string,
	options: { tableau?: string | null; inclureArchivees?: boolean } = {}
) => {
	const parametres = new URLSearchParams();
	if (options.tableau) parametres.set('tableau', options.tableau);
	if (options.inclureArchivees) parametres.set('inclure_archivees', 'true');
	const suffixe = parametres.toString() ? `?${parametres}` : '';

	return appeler<{ taches: TacheKanban[]; dependances: DependancesKanban }>(
		token,
		`/board${suffixe}`
	);
};

export const getFicheKanban = (token: string, id: string) =>
	appeler<FicheKanban>(token, `/tasks/${encodeURIComponent(id)}`);

/**
 * Debloquer une tache.
 *
 * Le proxy n'accepte que « ready », et le moteur applique ensuite sa propre
 * transition. Ce qui revient est l'etat REEL de la tache, jamais celui qu'on
 * esperait.
 */
export const debloquerTache = (token: string, id: string) =>
	appeler<TacheKanban>(token, `/tasks/${encodeURIComponent(id)}`, {
		methode: 'PATCH',
		corps: { statut: 'ready' }
	});

export const ecrireMessageKanban = (token: string, id: string, texte: string) =>
	appeler<MessageKanban>(token, `/tasks/${encodeURIComponent(id)}/comments`, {
		methode: 'POST',
		corps: { texte }
	});
