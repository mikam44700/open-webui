/**
 * Appels vers la page Moteur — LunarIA V2.
 *
 * Le navigateur ne parle jamais directement au moteur Hermes : il passe par le
 * backend d'Open WebUI, qui detient seul la cle d'acces. D'ou l'unique base
 * d'URL ci-dessous, et aucune adresse de moteur en dur cote client.
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';

const BASE = `${WEBUI_API_BASE_URL}/hermes`;

export type EtatMoteur = {
	joignable: boolean;
	version?: string | null;
	modele_actif?: string | null;
	fournisseur_actif?: string | null;
	detail?: string | null;
};

/**
 * Appel unique, factorise : toutes les routes de la page suivent le meme
 * schema (jeton en en-tete, erreur remontee lisible). Ecrire vingt fois le
 * meme bloc fetch serait vingt occasions de diverger.
 */
const appeler = async (
	token: string,
	chemin: string,
	options: { methode?: string; corps?: unknown; signal?: AbortSignal } = {}
) => {
	let erreur: string | null = null;

	const reponse = await fetch(`${BASE}${chemin}`, {
		method: options.methode ?? 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		signal: options.signal,
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

// --- Etat general -------------------------------------------------------

export const getEtatMoteur = (token: string): Promise<EtatMoteur> => appeler(token, '/status');

// --- Modeles IA ---------------------------------------------------------

export const getOptionsModeles = (token: string) => appeler(token, '/models/options');
export const getInfoModele = (token: string) => appeler(token, '/models/info');

export const changerDeModele = (token: string, model: string, provider?: string) =>
	appeler(token, '/models/set', { methode: 'POST', corps: { model, provider } });

export const getNiveauIntelligence = (token: string) => appeler(token, '/models/reasoning');

export const definirNiveauIntelligence = (token: string, effort: string) =>
	appeler(token, '/models/reasoning', { methode: 'POST', corps: { effort } });

// --- Modeles IA : sous-onglets ------------------------------------------

export type EtatDetaille = {
	version?: string;
	release_date?: string;
	can_update_hermes?: boolean;
	gateway_running?: boolean;
	gateway_state?: string;
	config_version?: number;
	latest_config_version?: number;
};

/** Sous-onglet « Moteur » : version, mise a jour, etat de la passerelle. */
export const getEtatDetaille = (token: string): Promise<EtatDetaille> =>
	appeler(token, '/engine/status');

/** Sous-onglet « Comptes » : fournisseurs a connexion par compte. */
export const getFournisseursCompte = (token: string) => appeler(token, '/providers/oauth');

export const demarrerOAuth = (token: string, providerId: string) =>
	appeler(token, `/providers/oauth/${encodeURIComponent(providerId)}/start`, { methode: 'POST' });

export const soumettreOAuth = (token: string, providerId: string, corps: Record<string, unknown>) =>
	appeler(token, `/providers/oauth/${encodeURIComponent(providerId)}/submit`, {
		methode: 'POST',
		corps
	});

export const suivreOAuth = (token: string, providerId: string, sessionId: string) =>
	appeler(
		token,
		`/providers/oauth/${encodeURIComponent(providerId)}/poll/${encodeURIComponent(sessionId)}`
	);

export const annulerOAuth = (token: string, sessionId: string) =>
	appeler(token, `/providers/oauth/sessions/${encodeURIComponent(sessionId)}`, {
		methode: 'DELETE'
	});

export const deconnecterOAuth = (token: string, providerId: string) =>
	appeler(token, `/providers/oauth/${encodeURIComponent(providerId)}`, { methode: 'DELETE' });

export const getClesFournisseurs = (token: string) => appeler(token, '/providers/keys');

export const verifierCleFournisseur = (token: string, key: string, value: string) =>
	appeler(token, '/providers/keys/validate', {
		methode: 'POST',
		corps: { key, value }
	});

export const enregistrerCleFournisseur = (token: string, key: string, value: string) =>
	appeler(token, `/providers/keys/${encodeURIComponent(key)}`, {
		methode: 'PUT',
		corps: { value }
	});

export const retirerCleFournisseur = (token: string, key: string) =>
	appeler(token, `/providers/keys/${encodeURIComponent(key)}`, { methode: 'DELETE' });

/** Sous-onglet « Local » : serveurs et adresses personnalisees. */
export const getServeursPersonnalises = (token: string) => appeler(token, '/providers/endpoints');

export const verifierServeurPersonnalise = (token: string, corps: Record<string, unknown>) =>
	appeler(token, '/providers/endpoints/validate', { methode: 'POST', corps });

export const enregistrerServeurPersonnalise = (token: string, corps: Record<string, unknown>) =>
	appeler(token, '/providers/endpoints', { methode: 'POST', corps });

export const activerServeurPersonnalise = (token: string, endpointId: string) =>
	appeler(token, `/providers/endpoints/${encodeURIComponent(endpointId)}/activate`, {
		methode: 'POST'
	});

export const retirerServeurPersonnalise = (token: string, endpointId: string) =>
	appeler(token, `/providers/endpoints/${encodeURIComponent(endpointId)}`, {
		methode: 'DELETE'
	});

/** Sous-onglet « Modèles IA combinés » : plusieurs cerveaux ensemble. */
export const getModelesCombines = (token: string) => appeler(token, '/models/moa');

// --- Messagerie ---------------------------------------------------------

export const getPlateformesMessagerie = (token: string) => appeler(token, '/messaging/platforms');

export const configurerPlateformeMessagerie = (
	token: string,
	platformId: string,
	corps: Record<string, unknown>
) =>
	appeler(token, `/messaging/platforms/${encodeURIComponent(platformId)}`, {
		methode: 'PUT',
		corps
	});

export const testerPlateformeMessagerie = (token: string, platformId: string) =>
	appeler(token, `/messaging/platforms/${encodeURIComponent(platformId)}/test`, {
		methode: 'POST'
	});

export const demarrerJumelageMessagerie = (
	token: string,
	platformId: string,
	corps: Record<string, unknown> = {}
) =>
	appeler(token, `/messaging/${encodeURIComponent(platformId)}/onboarding/start`, {
		methode: 'POST',
		corps
	});

export const suivreJumelageMessagerie = (
	token: string,
	platformId: string,
	pairingId: string
) =>
	appeler(
		token,
		`/messaging/${encodeURIComponent(platformId)}/onboarding/${encodeURIComponent(pairingId)}`
	);

export const appliquerJumelageMessagerie = (
	token: string,
	platformId: string,
	pairingId: string
) =>
	appeler(
		token,
		`/messaging/${encodeURIComponent(platformId)}/onboarding/${encodeURIComponent(pairingId)}/apply`,
		{ methode: 'POST' }
	);

export const annulerJumelageMessagerie = (
	token: string,
	platformId: string,
	pairingId: string
) =>
	appeler(
		token,
		`/messaging/${encodeURIComponent(platformId)}/onboarding/${encodeURIComponent(pairingId)}`,
		{ methode: 'DELETE' }
	);

// --- MCP ----------------------------------------------------------------

export const getServeursMcp = (token: string) => appeler(token, '/mcp/servers');
export const getCatalogueMcp = (token: string) => appeler(token, '/mcp/catalog');

export const basculerServeurMcp = (token: string, nom: string, enabled: boolean) =>
	appeler(token, `/mcp/servers/${encodeURIComponent(nom)}/enabled`, {
		methode: 'POST',
		corps: { enabled }
	});

export const ajouterServeurMcp = (token: string, corps: Record<string, unknown>) =>
	appeler(token, '/mcp/servers', { methode: 'POST', corps });

export const testerServeurMcp = (token: string, nom: string) =>
	appeler(token, `/mcp/servers/${encodeURIComponent(nom)}/test`, { methode: 'POST' });

export const authentifierServeurMcp = (token: string, nom: string) =>
	appeler(token, `/mcp/servers/${encodeURIComponent(nom)}/auth`, { methode: 'POST' });

export const suivreAuthentificationMcp = (token: string, flowId: string) =>
	appeler(token, `/mcp/oauth/flows/${encodeURIComponent(flowId)}`);

export const retirerServeurMcp = (token: string, nom: string) =>
	appeler(token, `/mcp/servers/${encodeURIComponent(nom)}`, { methode: 'DELETE' });

export const installerMcp = (
	token: string,
	name: string,
	env: Record<string, unknown> = {},
	enable = true
) =>
	appeler(token, '/mcp/catalog/install', {
		methode: 'POST',
		corps: { name, env, enable }
	});

// --- Outils, integrations, recherche web --------------------------------
// Les trois onglets lisent le meme inventaire : un seul appel, la page repartit.

export const getInventaireOutils = (token: string) => appeler(token, '/tools/toolsets');

export const basculerOutil = (token: string, nom: string, enabled: boolean) =>
	appeler(token, `/tools/toolsets/${encodeURIComponent(nom)}`, {
		methode: 'POST',
		corps: { enabled }
	});

export const getConfigurationOutil = (token: string, nom: string) =>
	appeler(token, `/tools/toolsets/${encodeURIComponent(nom)}/config`);

export const choisirFournisseurOutil = (
	token: string,
	nom: string,
	provider: string,
	capability?: 'search' | 'extract'
) =>
	appeler(token, `/tools/toolsets/${encodeURIComponent(nom)}/provider`, {
		methode: 'PUT',
		corps: { provider, ...(capability ? { capability } : {}) }
	});

export const enregistrerClesOutil = (
	token: string,
	nom: string,
	env: Record<string, string>
) =>
	appeler(token, `/tools/toolsets/${encodeURIComponent(nom)}/env`, {
		methode: 'PUT',
		corps: { env }
	});

export const getModelesOutil = (token: string, nom: string) =>
	appeler(token, `/tools/toolsets/${encodeURIComponent(nom)}/models`);

export const choisirModeleOutil = (
	token: string,
	nom: string,
	model: string,
	provider?: string
) =>
	appeler(token, `/tools/toolsets/${encodeURIComponent(nom)}/model`, {
		methode: 'PUT',
		corps: { model, ...(provider ? { provider } : {}) }
	});

export const finaliserConfigurationOutil = (token: string, nom: string, key: string) =>
	appeler(token, `/tools/toolsets/${encodeURIComponent(nom)}/post-setup`, {
		methode: 'POST',
		corps: { key }
	});

// --- Competences --------------------------------------------------------

export const getCompetences = (token: string) => appeler(token, '/skills');

export const basculerCompetence = (token: string, name: string, enabled: boolean) =>
	appeler(token, '/skills/toggle', { methode: 'POST', corps: { name, enabled } });

// --- Garde-fous ---------------------------------------------------------

/**
 * Un reglage d'encadrement lu dans la configuration du moteur.
 *
 * La valeur arrive brute : le backend lit, l'interface met en mots. Une liste
 * est deja reduite a sa longueur cote backend — c'est le nombre qui parle
 * (« aucune commande autorisee »), pas son contenu.
 */
export type GardeFou = {
	id: string;
	genre: 'texte' | 'bool' | 'nombre' | 'liste' | 'secondes';
	valeur: string | number | boolean;
};

export const getGardeFous = (
	token: string
): Promise<{ disponible: boolean; regles: GardeFou[] }> => appeler(token, '/guardrails');
