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

// --- Onboarding Telegram « managed bot » (parcours QR 1-clic) ----------------

export type TelegramPairingStart = {
	pairing_id: string;
	suggested_username: string;
	deep_link: string;
	qr_payload: string;
	expires_at: string | null;
};

export type TelegramPairingStatus = {
	status: 'waiting' | 'ready';
	bot_username: string | null;
	owner_user_id: number | null;
	expires_at: string | null;
};

export type TelegramPairingApplyResult = {
	ok: boolean;
	bot_username: string | null;
	owner_user_id: number | null;
	needs_restart: boolean;
	restart_ok: boolean;
	restart_error: string | null;
	error: string | null;
};

export const startTelegramPairing = (token: string) =>
	call(token, 'POST', '/platforms/telegram/pairing/start') as Promise<TelegramPairingStart>;

export const pollTelegramPairing = (token: string, pairingId: string) =>
	call(token, 'GET', `/platforms/telegram/pairing/${pairingId}`) as Promise<TelegramPairingStatus>;

export const applyTelegramPairing = (token: string, pairingId: string) =>
	call(token, 'POST', `/platforms/telegram/pairing/${pairingId}/apply`) as Promise<TelegramPairingApplyResult>;

export const cancelTelegramPairing = (token: string, pairingId: string) =>
	call(token, 'DELETE', `/platforms/telegram/pairing/${pairingId}`);

// --- Partage : allowlist des utilisateurs ------------------------------------

export type MessagingUser = {
	platform: string;
	user_id: string;
	user_name: string;
	approved_at: number | null;
	pending_code: string | null;
	age_minutes: number | null;
};

export type MessagingUsersResponse = {
	approved: MessagingUser[];
	pending: MessagingUser[];
};

export type MessagingActionResult = {
	ok: boolean;
	needs_restart: boolean;
	restart_ok: boolean;
	restart_error: string | null;
	error: string | null;
};

export const listPlatformUsers = (token: string, platformId: string) =>
	call(token, 'GET', `/platforms/${platformId}/users`) as Promise<MessagingUsersResponse>;

export const approvePlatformUser = (
	token: string,
	platformId: string,
	body: { code?: string; user_id?: string; user_name?: string }
) => call(token, 'POST', `/platforms/${platformId}/users`, body) as Promise<MessagingActionResult>;

export const revokePlatformUser = (token: string, platformId: string, userId: string) =>
	call(token, 'DELETE', `/platforms/${platformId}/users/${userId}`) as Promise<MessagingActionResult>;

export const disconnectPlatform = (token: string, platformId: string) =>
	call(token, 'POST', `/platforms/${platformId}/disconnect`) as Promise<MessagingActionResult>;
