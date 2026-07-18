import { apiCall } from '$lib/apis/apiCall';

// Client API des connecteurs MCP (onglet MCP de la page Hermes). Appelle le router bridge
// monté en direct sur /api/v1/mcp (gestion des MCP de Hermes — source de vérité unique).

// Helper interne : un appel JSON authentifié vers /api/v1/mcp, gestion d'erreur uniforme
// (mutualisée dans $lib/apis/apiCall).
const call = (token: string, method: string, path: string, body?: unknown) =>
	apiCall(token, '/mcp', method, path, body);

export const getConnectors = (token: string) => call(token, 'GET', '/connectors');

// US2 — catalogue + installation + clé + OAuth
export const getCatalog = (token: string) => call(token, 'GET', '/catalog');

export const installConnector = (token: string, fromCatalog: string) =>
	call(token, 'POST', '/connectors', { from_catalog: fromCatalog });

// Installe un MCP du registre distant (remote OAuth, ou stdio avec champs/clés résolus côté bridge).
export const installFromRegistry = (
	token: string,
	name: string,
	fields?: Record<string, string | string[]>
) => call(token, 'POST', '/connectors', { from_registry: name, fields: fields ?? {} });

export const getInstallStatus = (token: string, id: string) =>
	call(token, 'GET', `/connectors/${id}/install/status`);

export const setConnectorKey = (token: string, id: string, value: string) =>
	call(token, 'PUT', `/connectors/${id}/key`, { value });

export const startConnectorOAuth = (token: string, id: string) =>
	call(token, 'POST', `/connectors/${id}/oauth/start`);

export const getConnectorOAuthStatus = (token: string, id: string) =>
	call(token, 'GET', `/connectors/${id}/oauth/status`);

// US4 — gérer un connecteur
export const setConnectorEnabled = (token: string, id: string, enabled: boolean) =>
	call(token, 'PATCH', `/connectors/${id}`, { enabled });

export const testConnector = (token: string, id: string) =>
	call(token, 'POST', `/connectors/${id}/test`);

export const deleteConnector = (token: string, id: string) => call(token, 'DELETE', `/connectors/${id}`);

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
) => call(token, 'POST', '/connectors', payload);
