import {
	enregistrerClesOutil,
	getConfigurationOutil,
	getInventaireOutils
} from '$lib/apis/hermes';
import { INTEGRATION_FR } from '$lib/utils/integrationLabels';

const INTEGRATION_TOOL: Record<string, { tool: string; key?: string; auth_mode: string; subservices?: string[] }> = {
	'google-workspace': { tool: 'google', auth_mode: 'account', subservices: ['Gmail', 'Drive', 'Agenda'] },
	'microsoft-365': { tool: 'microsoft', auth_mode: 'account', subservices: ['Outlook', 'OneDrive', 'Agenda'] },
	notion: { tool: 'notion', key: 'NOTION_API_KEY', auth_mode: 'key' },
	github: { tool: 'github', key: 'GITHUB_TOKEN', auth_mode: 'key' },
	airtable: { tool: 'airtable', key: 'AIRTABLE_API_KEY', auth_mode: 'key' },
	obsidian: { tool: 'obsidian', key: 'OBSIDIAN_VAULT_PATH', auth_mode: 'path' },
	email: { tool: 'email', auth_mode: 'credentials' }
};

export const getIntegrations = async (token: string) => {
	const result = await getInventaireOutils(token);
	const tools = Array.isArray(result) ? result : result?.toolsets ?? [];
	const byName = new Map(tools.map((tool: any) => [`${tool.name}`, tool]));
	return {
		integrations: Object.keys(INTEGRATION_FR).map((id) => {
			const mapping = INTEGRATION_TOOL[id];
			const tool = mapping ? byName.get(mapping.tool) : null;
			const configured = Boolean(tool?.configured);
			return {
				id,
				auth_mode: mapping?.auth_mode ?? 'account',
				state: configured ? 'connected' : 'not_connected',
				secret_state: configured ? 'present' : 'absent',
				subservices: mapping?.subservices ?? [],
				visible: true,
				local_only: false,
				reason: mapping ? null : 'Connexion disponible via MCP'
			};
		})
	};
};

export const setIntegrationKey = async (token: string, id: string, value: string) => {
	const mapping = INTEGRATION_TOOL[id];
	if (!mapping?.key) throw new Error('Cette intégration utilise une connexion par compte.');
	return enregistrerClesOutil(token, mapping.tool, { [mapping.key]: value });
};
export const testIntegration = async (token: string, id: string) => {
	const mapping = INTEGRATION_TOOL[id];
	if (!mapping) return { state: 'not_connected', reason: 'Connexion disponible via MCP.' };
	const result = await getConfigurationOutil(token, mapping.tool);
	return { state: result?.configured ? 'connected' : 'not_connected', reason: result?.reason };
};
export const disconnectIntegration = async () => ({ ok: false, unavailable: true });
export const getOAuthAuthUrl = async () => ({ auth_url: null });
export const exchangeOAuth = async () => ({ ok: false, unavailable: true });
export const getOAuthStatus = async () => ({ connected: false });
export const disconnectOAuth = async () => ({ ok: false, unavailable: true });
export const guessEmailServers = async (_token: string, email: string) => {
	const domain = email.split('@')[1] ?? '';
	return { imap_host: `imap.${domain}`, smtp_host: `smtp.${domain}` };
};
export const setEmailCredentials = async () => ({ ok: false, unavailable: true });
export const setGoogleClientSecret = async () => ({ ok: false, unavailable: true });
export const getGoogleAuthUrl = async () => ({ auth_url: null });
export const submitGoogleAuthCode = async () => ({ ok: false, unavailable: true });
export const getGoogleStatus = async () => ({ connected: false });
