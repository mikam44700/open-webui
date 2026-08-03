import { WEBUI_BASE_URL } from '$lib/constants';

const BASE = `${WEBUI_BASE_URL}/api/v1/composio`;

/**
 * Toutes les routes suivent le meme schema que celles du moteur : jeton en
 * en-tete, erreur remontee lisible. Le navigateur ne joint jamais Composio
 * directement — le backend garde la cle et assainit les erreurs amont.
 */
const appeler = async (
	token: string,
	chemin: string,
	options: { methode?: string; corps?: unknown } = {}
) => {
	let erreur: string | null = null;

	const reponse = await fetch(`${BASE}${chemin}`, {
		method: options.methode ?? 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(options.corps !== undefined ? { body: JSON.stringify(options.corps) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			erreur = err?.detail ?? `${err}`;
			return null;
		});

	if (erreur) throw erreur;
	return reponse;
};

export type EtatComposio = {
	cle: boolean;
	etat: 'absente' | 'ok' | 'refusee' | 'injoignable';
	detail?: string | null;
};

export type ApplicationComposio = {
	slug: string;
	nom: string;
	logo?: string | null;
	/** Phrase fournie par Composio, en anglais. */
	description?: string | null;
	/** Nombre d'actions que l'assistant pourra declencher. */
	actions?: number | null;
	categories?: string[];
	site?: string | null;
	sans_compte?: boolean;
};

export type ConnexionComposio = {
	id: string;
	application: string;
	etat: string;
};

export const getEtatComposio = (token: string): Promise<EtatComposio> => appeler(token, '/status');

export const verifierCleComposio = (
	token: string,
	value: string
): Promise<{ valide: boolean; motif?: string | null }> =>
	appeler(token, '/key/validate', { methode: 'POST', corps: { value } });

export const enregistrerCleComposio = (token: string, value: string) =>
	appeler(token, '/key', { methode: 'PUT', corps: { value } });

export const retirerCleComposio = (token: string) => appeler(token, '/key', { methode: 'DELETE' });

export const getApplicationsComposio = (
	token: string
): Promise<{ applications: ApplicationComposio[] }> => appeler(token, '/toolkits');

export const getConnexionsComposio = (
	token: string
): Promise<{ connexions: ConnexionComposio[] }> => appeler(token, '/connections');

export const connecterApplication = (
	token: string,
	toolkit: string,
	callbackUrl?: string
): Promise<{ url: string; id: string; expire_le?: string | null }> =>
	appeler(token, '/connections', {
		methode: 'POST',
		corps: { toolkit, callback_url: callbackUrl }
	});

export const suivreConnexion = (token: string, id: string): Promise<ConnexionComposio> =>
	appeler(token, `/connections/${encodeURIComponent(id)}`);

export const retirerConnexion = (token: string, id: string) =>
	appeler(token, `/connections/${encodeURIComponent(id)}`, { methode: 'DELETE' });

export type BranchementMoteur = {
	branche: boolean;
	etat: 'present' | 'absent' | 'injoignable';
	actif?: boolean;
	url?: string | null;
	detail?: string | null;
};

export const getBranchementMoteur = (token: string): Promise<BranchementMoteur> =>
	appeler(token, '/engine');

/** L'adresse MCP est demandée à Composio à partir de la clé : rien à fournir. */
export const brancherMoteur = (token: string): Promise<{ ok: boolean; serveurs: string[] }> =>
	appeler(token, '/engine', { methode: 'POST', corps: {} });

export const debrancherMoteur = (token: string) => appeler(token, '/engine', { methode: 'DELETE' });
