import { WEBUI_API_BASE_URL } from '$lib/constants';

// Helper interne : un appel JSON authentifié vers /api/v1/gateway
const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/gateway${path}`, {
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

export type GatewayStatus = {
	running: boolean;
	port: number;
	api_key_present: boolean;
};

export type MessagingEnvVar = {
	key: string;
	prompt: string;
	description: string;
	required: boolean;
	is_password: boolean;
	advanced: boolean;
	is_set: boolean;
	redacted_value: string;
};

export type MessagingPlatform = {
	id: string;
	name: string;
	emoji: string;
	description: string;
	docs_url: string;
	configured: boolean;
	enabled: boolean;
	state: 'disabled' | 'needs_setup' | 'ready' | 'connected';
	env_vars: MessagingEnvVar[];
};

export type MessagingPlatformsResponse = {
	platforms: MessagingPlatform[];
	gateway_running: boolean;
};

export const getGatewayStatus = (token: string) => call(token, 'GET', '/status');

export const getMessagingPlatforms = (token: string) => call(token, 'GET', '/platforms');

export const updateMessagingPlatform = (
	token: string,
	platformId: string,
	update: { env?: Record<string, string>; clear_env?: string[]; enabled?: boolean }
) => call(token, 'POST', `/platforms/${platformId}`, update);

export const testMessagingPlatform = (token: string, platformId: string) =>
	call(token, 'POST', `/platforms/${platformId}/test`);

export const generateApiServerKey = (token: string) => call(token, 'POST', '/api-key/generate');

export const restartGateway = (token: string) => call(token, 'POST', '/restart');
