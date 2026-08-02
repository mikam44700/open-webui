import {
	ajouterServeurMcp,
	authentifierServeurMcp,
	basculerServeurMcp,
	enregistrerClesOutil,
	getCatalogueMcp,
	getServeursMcp,
	installerMcp,
	retirerServeurMcp,
	suivreAuthentificationMcp,
	testerServeurMcp
} from '$lib/apis/hermes';

const oauthFlows = new Map<string, string>();

export const getConnectors = async (token: string) => {
	const result = await getServeursMcp(token);
	return {
		connectors: (result?.servers ?? []).map((server: any) => ({
			id: `${server.name}`,
			transport: server.transport ?? (server.url ? 'http' : 'stdio'),
			auth_type: server.auth_type ?? server.auth ?? 'none',
			enabled: Boolean(server.enabled),
			state: !server.enabled
				? 'disabled'
				: server.auth_required
					? 'auth_required'
					: server.error
						? 'error'
						: server.tools?.length
							? 'connected'
							: 'disconnected',
			endpoint: server.url ?? server.command,
			secret_state: Object.keys(server.env ?? {}).length ? 'present' : 'absent',
			source: server.source ?? null
		}))
	};
};

export const getCatalog = async (token: string) => {
	const result = await getCatalogueMcp(token);
	return {
		...result,
		entries: (result?.entries ?? []).map((entry: any) => ({
			...entry,
			transport: entry.transport ?? (entry.url ? 'http' : 'stdio'),
			auth_type: entry.auth_type === 'api_key' ? 'key' : (entry.auth_type ?? 'none'),
			installable: entry.installable !== false,
			install_method: entry.install_method ?? 'engine',
			config_fields: entry.config_fields ?? (entry.required_env ?? []).map((key: string) => ({
				key,
				label: key,
				type: 'string',
				secret: true,
				required: true
			}))
		}))
	};
};

export const installConnector = (token: string, fromCatalog: string) =>
	installerMcp(token, fromCatalog, {}, true);
export const installFromRegistry = (token: string, name: string, fields: Record<string, any> = {}) =>
	installerMcp(token, name, fields, true);
export const getInstallStatus = async () => ({ started: true, running: false, success: true });
export const setConnectorKey = (token: string, id: string, value: string) =>
	enregistrerClesOutil(token, id, { API_KEY: value });
export const startConnectorOAuth = async (token: string, id: string) => {
	const result = await authentifierServeurMcp(token, id);
	const flowId = `${result?.flow_id ?? result?.id ?? ''}`;
	if (flowId) oauthFlows.set(id, flowId);
	return result;
};
export const getConnectorOAuthStatus = async (token: string, id: string) => {
	const flowId = oauthFlows.get(id);
	if (!flowId) return { started: false, running: false, success: false };
	const result = await suivreAuthentificationMcp(token, flowId);
	const status = `${result?.status ?? ''}`.toLowerCase();
	return {
		...result,
		started: true,
		running: !['success', 'connected', 'complete', 'completed', 'error', 'failed'].includes(status),
		success: ['success', 'connected', 'complete', 'completed'].includes(status)
	};
};
export const setConnectorEnabled = (token: string, id: string, enabled: boolean) =>
	basculerServeurMcp(token, id, enabled);
export const testConnector = (token: string, id: string) => testerServeurMcp(token, id);
export const deleteConnector = (token: string, id: string) => retirerServeurMcp(token, id);
export const addCustomConnector = (token: string, payload: Record<string, unknown>) =>
	ajouterServeurMcp(token, payload);
