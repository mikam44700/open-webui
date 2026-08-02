import {
	annulerJumelageMessagerie,
	appliquerJumelageMessagerie,
	configurerPlateformeMessagerie,
	demarrerJumelageMessagerie,
	getEtatDetaille,
	getPlateformesMessagerie,
	suivreJumelageMessagerie,
	testerPlateformeMessagerie
} from '$lib/apis/hermes';

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
	available?: boolean;
	unavailable_reason?: string;
	recommended?: boolean;
	expert_only?: boolean;
};

let platformCache: MessagingPlatform[] = [];

export const getGatewayStatus = async (token: string) => {
	const status = await getEtatDetaille(token);
	return { running: Boolean(status?.gateway_running), port: 0, api_key_present: true };
};
export const getMessagingPlatforms = async (token: string) => {
	const result = await getPlateformesMessagerie(token);
	platformCache = result?.platforms ?? [];
	return result;
};
export const updateMessagingPlatform = (
	token: string,
	platformId: string,
	update: { env?: Record<string, string>; clear_env?: string[]; enabled?: boolean }
) => configurerPlateformeMessagerie(token, platformId, update);
export const testMessagingPlatform = (token: string, platformId: string) =>
	testerPlateformeMessagerie(token, platformId);
export const generateApiServerKey = async () => ({ ok: false, unavailable: true });
export const restartGateway = async () => ({ ok: true, needs_restart: false });

export const startTelegramPairing = (token: string) =>
	demarrerJumelageMessagerie(token, 'telegram');
export const pollTelegramPairing = (token: string, pairingId: string) =>
	suivreJumelageMessagerie(token, 'telegram', pairingId);
export const applyTelegramPairing = (token: string, pairingId: string) =>
	appliquerJumelageMessagerie(token, 'telegram', pairingId);
export const cancelTelegramPairing = (token: string, pairingId: string) =>
	annulerJumelageMessagerie(token, 'telegram', pairingId);

const botInfo = (id: string) => {
	const platform = platformCache.find((item) => item.id === id);
	return { username: null, name: platform?.name ?? null, link: null };
};
export const getTelegramBotInfo = async () => botInfo('telegram');
export const getDiscordBotInfo = async () => ({
	name: botInfo('discord').name,
	application_id: null,
	invite_url: null
});
export const getSlackBotInfo = async () => ({
	name: botInfo('slack').name,
	team_name: null,
	workspace_url: null
});

export const applyDiscord = async (token: string, botToken: string) => {
	await configurerPlateformeMessagerie(token, 'discord', {
		env: { DISCORD_BOT_TOKEN: botToken },
		enabled: true
	});
	const tested = await testerPlateformeMessagerie(token, 'discord');
	return { ok: tested?.ok === true, bot_name: null, invite_url: null, needs_restart: false, restart_ok: true, restart_error: null, error: tested?.reason ?? null };
};
export const applySlack = async (token: string, botToken: string, appToken: string) => {
	await configurerPlateformeMessagerie(token, 'slack', {
		env: { SLACK_BOT_TOKEN: botToken, SLACK_APP_TOKEN: appToken },
		enabled: true
	});
	const tested = await testerPlateformeMessagerie(token, 'slack');
	return { ok: tested?.ok === true, bot_name: null, team_name: null, workspace_url: null, needs_restart: false, restart_ok: true, restart_error: null, error: tested?.reason ?? null };
};
export const applyEmail = async (
	token: string,
	address: string,
	password: string,
	imapHost: string,
	smtpHost: string
) => {
	await configurerPlateformeMessagerie(token, 'email', {
		env: {
			EMAIL_ADDRESS: address,
			EMAIL_PASSWORD: password,
			IMAP_HOST: imapHost,
			SMTP_HOST: smtpHost
		},
		enabled: true
	});
	const tested = await testerPlateformeMessagerie(token, 'email');
	return { ok: tested?.ok === true, address, mailbox_count: null, needs_restart: false, restart_ok: true, restart_error: null, error: tested?.reason ?? null };
};

export const listPlatformUsers = async () => ({ approved: [], pending: [] });
export const approvePlatformUser = async () => ({ ok: false, needs_restart: false, restart_ok: false, restart_error: null, error: 'Gestion des utilisateurs indisponible.' });
export const revokePlatformUser = async () => ({ ok: false, needs_restart: false, restart_ok: false, restart_error: null, error: 'Gestion des utilisateurs indisponible.' });
export const disconnectPlatform = async (token: string, platformId: string) => {
	const platform = platformCache.find((item) => item.id === platformId);
	await configurerPlateformeMessagerie(token, platformId, {
		enabled: false,
		clear_env: (platform?.env_vars ?? []).map((env) => env.key)
	});
	return { ok: true, needs_restart: false, restart_ok: true, restart_error: null, error: null };
};
