import { WEBUI_API_BASE_URL } from '$lib/constants';

// Le tableau de bord du travail (SPEC-kanban-taches) : les tâches vivent dans le
// moteur Hermes, le backend les expose via les verbes officiels — jamais la base.

export type ColonneKanban = {
	cle: string;
	titre: string;
	aide: string;
};

export type PrioriteKanban = 'urgent' | 'eleve' | 'bas' | null;

export type TacheKanban = {
	id: string;
	titre: string;
	description: string | null;
	colonne: string;
	agent: string | null;
	bloquee: boolean;
	priorite: PrioriteKanban;
	cree_le: number | null;
};

export type ExecutionKanban = {
	agent: string | null;
	issue: string | null;
	resume: string | null;
	erreur: string | null;
	debut: number | null;
};

export type CommentaireKanban = {
	auteur: string | null;
	texte: string;
	le: number | null;
};

export type EtapeHistoriqueKanban = {
	libelle: string;
	le: number | null;
};

export type DetailTacheKanban = {
	tache: TacheKanban;
	dernier_resume: string | null;
	resultat: string | null;
	executions: ExecutionKanban[];
	commentaires: CommentaireKanban[];
	historique: EtapeHistoriqueKanban[];
};

export type TableauKanban = {
	colonnes: ColonneKanban[];
	taches: TacheKanban[];
	total: number;
};

const entetes = (token: string) => ({
	Accept: 'application/json',
	'Content-Type': 'application/json',
	authorization: `Bearer ${token}`
});

const lire = async (res: Response) => {
	if (!res.ok) {
		const corps = await res.json().catch(() => null);
		throw corps?.detail ?? 'Le tableau des tâches est indisponible.';
	}
	return res.json();
};

export const getBoard = async (token: string): Promise<TableauKanban> => {
	return fetch(`${WEBUI_API_BASE_URL}/kanban/board`, {
		method: 'GET',
		headers: entetes(token)
	}).then(lire);
};

export const createTask = async (
	token: string,
	titre: string,
	description?: string,
	priorite: 'urgent' | 'eleve' | 'normal' | 'bas' = 'normal'
): Promise<TacheKanban> => {
	return fetch(`${WEBUI_API_BASE_URL}/kanban/tasks`, {
		method: 'POST',
		headers: entetes(token),
		body: JSON.stringify({ titre, description: description || null, priorite })
	}).then(lire);
};

export const getTask = async (token: string, id: string): Promise<DetailTacheKanban> => {
	return fetch(`${WEBUI_API_BASE_URL}/kanban/tasks/${encodeURIComponent(id)}`, {
		method: 'GET',
		headers: entetes(token)
	}).then(lire);
};

export const moveTask = async (
	token: string,
	id: string,
	vers: 'a_faire' | 'en_cours' | 'termine'
): Promise<TacheKanban> => {
	return fetch(`${WEBUI_API_BASE_URL}/kanban/tasks/${encodeURIComponent(id)}/move`, {
		method: 'POST',
		headers: entetes(token),
		body: JSON.stringify({ vers })
	}).then(lire);
};
