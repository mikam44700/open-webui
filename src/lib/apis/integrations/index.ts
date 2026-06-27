import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de l'onglet Intégrations (Agent OS). Appelle le router admin /api/v1/integrations,
// qui proxifie vers le Providers Bridge (skills connectables de Hermes — source de vérité unique).
// Cf. specs/004-integrations.

const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/integrations${path}`, {
		method,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// US1 — lister les intégrations connectables avec leur état réel
export const getIntegrations = (token: string) => call(token, 'GET', '/');

// US2 — connexion par clé / chemin + test (Notion, GitHub, Airtable, Obsidian)
export const setIntegrationKey = (token: string, id: string, value: string) =>
	call(token, 'PUT', `/${id}/key`, { value });

export const testIntegration = (token: string, id: string) => call(token, 'POST', `/${id}/test`);

// Email (IMAP/SMTP)
export const guessEmailServers = (token: string, email: string) =>
	call(token, 'POST', '/email/guess', { email });

export const setEmailCredentials = (
	token: string,
	payload: {
		email: string;
		password: string;
		imap_host: string;
		imap_port: number;
		smtp_host: string;
		smtp_port: number;
	}
) => call(token, 'POST', '/email/credentials', payload);

// US3 — connexion Google Workspace (le client fournit son app Google)
export const setGoogleClientSecret = (token: string, clientSecretJson: unknown) =>
	call(token, 'POST', '/google-workspace/google/client-secret', {
		client_secret_json: clientSecretJson
	});

export const getGoogleAuthUrl = (token: string) =>
	call(token, 'POST', '/google-workspace/google/auth-url');

export const submitGoogleAuthCode = (token: string, code: string) =>
	call(token, 'POST', '/google-workspace/google/auth-code', { code });

export const getGoogleStatus = (token: string) =>
	call(token, 'GET', '/google-workspace/google/status');

// US4 — déconnecter une intégration
export const disconnectIntegration = (token: string, id: string) =>
	call(token, 'DELETE', `/${id}/disconnect`);

// OAuth centralisé (1 clic) — Microsoft 365 et futurs providers OAuth gérés par le bridge.
// Ces fonctions proxifient vers /integrations/oauth/{provider_id}/* côté bridge.

/** Récupère l'URL d'autorisation OAuth du fournisseur (redirige l'utilisateur vers celle-ci). */
export const getOAuthAuthUrl = (token: string, providerId: string) =>
	call(token, 'GET', `/oauth/${providerId}/auth-url`);

/** Échange le code de retour OAuth contre un token stocké côté bridge. */
export const exchangeOAuth = (token: string, providerId: string, code: string, state: string) =>
	call(token, 'POST', `/oauth/${providerId}/exchange`, { code, state });

/** Retourne l'état de connexion OAuth du fournisseur (connected | not_connected). */
export const getOAuthStatus = (token: string, providerId: string) =>
	call(token, 'GET', `/oauth/${providerId}/status`);

/** Déconnecte (révoque) un provider OAuth centralisé. */
export const disconnectOAuth = (token: string, providerId: string) =>
	call(token, 'DELETE', `/oauth/${providerId}`);
