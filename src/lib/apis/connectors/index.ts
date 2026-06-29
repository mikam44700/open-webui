import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de la page Connecteurs (Agent OS). Appelle le router admin /api/v1/connectors,
// qui proxifie vers le Providers Bridge (gestion des MCP de Hermes — source de vérité unique).

// Helper interne : un appel JSON authentifié vers /api/v1/connectors, gestion d'erreur uniforme.
const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/connectors${path}`, {
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

export const getConnectors = (token: string) => call(token, 'GET', '/');

// US2 — catalogue + installation + clé + OAuth
export const getCatalog = (token: string) => call(token, 'GET', '/catalog');

export const installConnector = (token: string, fromCatalog: string) =>
	call(token, 'POST', '/', { from_catalog: fromCatalog });

// Installe un MCP du registre distant (remote OAuth, ou stdio avec champs/clés résolus côté bridge).
export const installFromRegistry = (
	token: string,
	name: string,
	fields?: Record<string, string | string[]>
) => call(token, 'POST', '/', { from_registry: name, fields: fields ?? {} });

export const getInstallStatus = (token: string, id: string) =>
	call(token, 'GET', `/${id}/install/status`);

export const setConnectorKey = (token: string, id: string, value: string) =>
	call(token, 'PUT', `/${id}/key`, { value });

export const startConnectorOAuth = (token: string, id: string) =>
	call(token, 'POST', `/${id}/oauth/start`);

export const getConnectorOAuthStatus = (token: string, id: string) =>
	call(token, 'GET', `/${id}/oauth/status`);

// US4 — gérer un connecteur
export const setConnectorEnabled = (token: string, id: string, enabled: boolean) =>
	call(token, 'PATCH', `/${id}`, { enabled });

export const testConnector = (token: string, id: string) => call(token, 'POST', `/${id}/test`);

export const deleteConnector = (token: string, id: string) => call(token, 'DELETE', `/${id}`);

// US5 — ajouter un connecteur custom (http/stdio)
export const addCustomConnector = (
	token: string,
	payload: {
		name: string;
		transport: string;
		url?: string;
		command?: string;
		args?: string[];
		env?: Record<string, string>;
		auth_type?: string;
	}
) => call(token, 'POST', '/', payload);
