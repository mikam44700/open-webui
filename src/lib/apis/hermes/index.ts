import { WEBUI_API_BASE_URL } from '$lib/constants';

export type HermesStatus = {
	configured: boolean;
	state:
		| 'operational'
		| 'degraded'
		| 'not_configured'
		| 'unavailable'
		| 'authentication_failed'
		| string;
	version: string | null;
	model: string | null;
	active_agents: number;
	gateway_state?: string | null;
	gateway_busy?: boolean;
	updated_at?: string | null;
	platforms?: Record<string, unknown>;
	readiness?: Record<string, unknown>;
};

export type HermesCapabilities = {
	model?: string;
	features?: Record<string, boolean | string | number | null>;
	endpoints?: Record<string, { method?: string; path?: string }>;
	runtime?: {
		mode?: string;
		tool_execution?: string;
		description?: string;
	};
};

const request = async <T>(token: string, path: string): Promise<T> => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/hermes${path}`, {
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!response.ok) {
		const body = await response.json().catch(() => null);
		throw body?.detail?.error ?? body?.detail ?? new Error('Hermes Agent request failed');
	}

	return response.json();
};

export const getHermesStatus = (token: string) => request<HermesStatus>(token, '/status');

export const getHermesCapabilities = (token: string) =>
	request<HermesCapabilities>(token, '/capabilities');

export const getHermesSkills = (token: string) =>
	request<Record<string, unknown>>(token, '/skills');

export const getHermesToolsets = (token: string) =>
	request<Record<string, unknown>>(token, '/toolsets');
