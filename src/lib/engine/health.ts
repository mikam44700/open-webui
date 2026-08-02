/**
 * Dérivation de l'état du moteur (Hermes Agent).
 *
 * Fonctions PURES (aucune I/O) : elles prennent la réponse déjà chargée et renvoient ce qu'il
 * faut afficher. Isolées ici pour être testables unitairement — c'est la partie la plus à
 * risque, celle qui décide si un moteur mort est annoncé « opérationnel ».
 *
 * Honnêteté : un état `unknown` (source injoignable, champ absent) n'est jamais présenté
 * comme une panne. Seul un état réellement `down` déclenche une alerte de panne.
 *
 * Les libellés renvoyés sont des CLÉS i18n, jamais du texte traduit : la traduction reste
 * la responsabilité des composants, et les tests restent indépendants de la langue.
 */

import type { HermesStatus } from '$lib/apis/hermes';

export type DisplayState = 'ok' | 'warning' | 'down' | 'unknown';

/** Sonde de readiness telle que renvoyée par `/health/detailed`. */
export type ReadinessCheck = {
	status?: string;
	state?: string;
	detail?: string;
	used_percent?: number;
	free_bytes?: number;
	connected_platforms?: number;
	platforms?: number;
	active_api_runs?: number;
	active_delegations?: number;
	process_completions?: number;
};

export type HealthRow = {
	labelKey: string;
	state: DisplayState;
	/** Détail non traduisible : version, nom de modèle. */
	detail?: string;
	/** Détail traduisible, prioritaire sur `detail`. */
	detailKey?: string;
	detailParams?: Record<string, string | number>;
	/** Le moteur lui-même, par opposition à l'un de ses composants. */
	overall?: boolean;
};

export type EngineIssue = {
	titleKey: string;
	descriptionKey: string;
	descriptionParams?: Record<string, string>;
	hintKey?: string;
};

export type PlatformRow = { name: string; state: DisplayState };

export type ActivityCounters = {
	activeAgents: number;
	apiRuns: number;
	delegations: number;
	pendingCompletions: number;
};

export type CapabilityGroup = {
	titleKey: string;
	items: { name: string; enabled: boolean }[];
};

export type AlertSeverity = 'critical' | 'warning' | 'info';

export type EngineAlert = {
	severity: AlertSeverity;
	messageKey: string;
	/** Clé du composant concerné, à traduire puis injecter dans `messageKey`. */
	componentKey?: string;
	messageParams?: Record<string, string | number>;
	/**
	 * Page qui règle le problème, quand elle existe. Aucune alerte ne doit être un
	 * cul-de-sac : à défaut de lien, `hintKey` donne l'action concrète à mener.
	 */
	href?: string;
	/**
	 * Conseil de résolution, pour les causes qui se règlent hors de l'interface — la
	 * configuration de Hermes vit dans des variables d'environnement du serveur.
	 */
	hintKey?: string;
};

/** Pages d'Open WebUI capables de résoudre le problème d'un composant donné. */
const RESOLUTION_PAGES: Record<string, string> = {
	'AI model': '/workspace/models'
};

const OK_WORDS = new Set(['ok', 'ready', 'healthy', 'running', 'connected', 'operational']);
const WARNING_WORDS = new Set(['warning', 'degraded', 'busy', 'draining']);
const DOWN_WORDS = new Set(['error', 'failed', 'down', 'stopped', 'disconnected', 'unavailable']);

/** État d'une sonde. Un mot inconnu reste `unknown` : on n'invente pas une panne. */
export const checkState = (check?: ReadinessCheck | null): DisplayState => {
	const value = String(check?.status ?? check?.state ?? '')
		.trim()
		.toLowerCase();
	if (OK_WORDS.has(value)) return 'ok';
	if (WARNING_WORDS.has(value)) return 'warning';
	if (DOWN_WORDS.has(value)) return 'down';
	return 'unknown';
};

/** État global du moteur, déduit du `state` que le proxy renvoie toujours. */
export const engineState = (status: HermesStatus | null): DisplayState => {
	if (!status?.state) return 'unknown';
	if (status.state === 'operational') return 'ok';
	if (status.state === 'degraded') return 'warning';
	return 'down';
};

const checksOf = (status: HermesStatus | null): Record<string, ReadinessCheck> => {
	const checks = status?.readiness?.checks;
	return checks && typeof checks === 'object' ? (checks as Record<string, ReadinessCheck>) : {};
};

/**
 * Les six sondes exposées par Hermes, dans l'ordre de gravité pour un administrateur.
 * `formatBytes` est injecté pour que ce module reste sans dépendance d'affichage.
 */
export const buildHealthRows = (
	status: HermesStatus | null,
	formatBytes: (bytes: number) => string
): HealthRow[] => {
	const checks = checksOf(status);
	const disk = checks.disk ?? {};
	const gateway = checks.gateway ?? {};
	const hasPlatformCount = typeof gateway.platforms === 'number' && gateway.platforms > 0;
	const hasDiskUsage = typeof disk.used_percent === 'number';
	const hasFreeSpace = typeof disk.free_bytes === 'number';

	// Chaque ligne est rattachée à sa sonde : une sonde que Hermes n'a pas rapportée
	// disparaît de la liste au lieu d'y laisser un « inconnu » permanent.
	const rows: { probe?: string; row: HealthRow }[] = [
		{
			row: {
				labelKey: 'Engine',
				state: engineState(status),
				detail: status?.version ? `v${status.version}` : undefined,
				overall: true
			}
		},
		{
			probe: 'model',
			row: {
				labelKey: 'AI model',
				state: checkState(checks.model),
				detail: status?.model ?? undefined
			}
		},
		{
			probe: 'gateway',
			row: {
				labelKey: 'Messaging',
				state: checkState(gateway),
				detailKey: hasPlatformCount ? '{{connected}} of {{total}} connected' : undefined,
				detailParams: hasPlatformCount
					? { connected: gateway.connected_platforms ?? 0, total: gateway.platforms as number }
					: undefined
			}
		},
		{
			probe: 'state_db',
			row: { labelKey: 'Working memory', state: checkState(checks.state_db) }
		},
		{
			probe: 'config',
			row: { labelKey: 'Settings', state: checkState(checks.config) }
		},
		{
			probe: 'disk',
			row: {
				labelKey: 'Storage space',
				state: checkState(disk),
				detailKey: hasDiskUsage
					? hasFreeSpace
						? '{{percent}}% used, {{free}} free'
						: '{{percent}}% used'
					: undefined,
				detailParams: hasDiskUsage
					? {
							percent: disk.used_percent as number,
							...(hasFreeSpace ? { free: formatBytes(disk.free_bytes as number) } : {})
						}
					: undefined
			}
		}
	];

	return rows.filter(({ probe }) => probe === undefined || probe in checks).map(({ row }) => row);
};

/** Libellés des composants en défaut, moteur lui-même exclu. */
export const failingComponents = (rows: HealthRow[]): string[] =>
	rows
		.filter((row) => !row.overall && (row.state === 'warning' || row.state === 'down'))
		.map((row) => row.labelKey);

/** Plateformes déclarées par la passerelle, triées par nom pour un affichage stable. */
export const buildPlatformRows = (status: HermesStatus | null): PlatformRow[] => {
	const platforms = status?.platforms;
	if (!platforms || typeof platforms !== 'object') return [];

	return Object.entries(platforms)
		.map(([name, value]) => ({
			name,
			state: checkState(value as ReadinessCheck)
		}))
		.sort((a, b) => a.name.localeCompare(b.name));
};

export const buildActivity = (status: HermesStatus | null): ActivityCounters => {
	const queues = checksOf(status).background_queues ?? {};
	const positive = (value: unknown) => (typeof value === 'number' && value > 0 ? value : 0);

	return {
		activeAgents: positive(status?.active_agents),
		apiRuns: positive(queues.active_api_runs),
		delegations: positive(queues.active_delegations),
		pendingCompletions: positive(queues.process_completions)
	};
};

const CAPABILITY_GROUPS: { titleKey: string; names: string[] }[] = [
	{
		titleKey: 'Conversation',
		names: [
			'chat_completions',
			'chat_completions_streaming',
			'responses_api',
			'responses_streaming'
		]
	},
	{
		titleKey: 'Executions',
		names: [
			'run_submission',
			'run_status',
			'run_events_sse',
			'run_stop',
			'run_approval_response',
			'tool_progress_events',
			'approval_events'
		]
	},
	{
		titleKey: 'Sessions',
		names: [
			'session_resources',
			'session_chat',
			'session_chat_streaming',
			'session_fork',
			'session_model_lock',
			'model_options'
		]
	},
	{
		titleKey: 'Administration',
		names: [
			'admin_config_rw',
			'jobs_admin',
			'memory_write_api',
			'skills_api',
			'audio_api',
			'realtime_voice'
		]
	}
];

/**
 * Regroupe les capacités par famille, en conservant celles qui sont DÉSACTIVÉES : savoir
 * ce que le moteur ne sait pas faire vaut autant que l'inverse. Les valeurs non booléennes
 * (en-têtes de session, drapeaux techniques) ne sont pas des capacités et sont écartées.
 */
export const groupCapabilities = (
	features: Record<string, boolean | string | number | null> | undefined
): CapabilityGroup[] => {
	if (!features) return [];
	const booleans = new Map<string, boolean>();
	for (const [name, value] of Object.entries(features)) {
		if (typeof value === 'boolean') booleans.set(name, value);
	}

	const groups: CapabilityGroup[] = [];
	const claimed = new Set<string>();

	for (const group of CAPABILITY_GROUPS) {
		const items = group.names
			.filter((name) => booleans.has(name))
			.map((name) => {
				claimed.add(name);
				return { name, enabled: booleans.get(name) as boolean };
			});
		if (items.length) groups.push({ titleKey: group.titleKey, items });
	}

	const others = [...booleans.keys()]
		.filter((name) => !claimed.has(name))
		.map((name) => ({ name, enabled: booleans.get(name) as boolean }));
	if (others.length) groups.push({ titleKey: 'Other capabilities', items: others });

	return groups;
};

/**
 * Message de panne actionnable. Le backend distingue chaque cause : on ne les écrase pas
 * dans un message générique, sinon un administrateur qui n'a rien configuré voit le même
 * écran que celui dont la clé est refusée.
 *
 * `components` reçoit des libellés DÉJÀ traduits (le composant appelant s'en charge).
 */
export const deriveIssue = (state: string | undefined, components: string[] = []): EngineIssue => {
	switch (state) {
		case 'not_configured':
			return {
				titleKey: 'Hermes Agent is not configured',
				descriptionKey: 'Open WebUI does not know where to reach the engine yet.',
				hintKey: 'Set HERMES_API_URL on the server, then restart Open WebUI.'
			};
		case 'authentication_failed':
			return {
				titleKey: 'Hermes Agent refused the credentials',
				descriptionKey: 'The engine answered, but rejected the configured API key.',
				hintKey: 'Check HERMES_API_KEY, or the key stored in the Hermes configuration file.'
			};
		case 'unavailable':
			return {
				titleKey: 'Hermes Agent is unreachable',
				descriptionKey:
					'The engine did not answer. It may be stopped, or the address may be wrong.',
				hintKey: 'Make sure Hermes Agent is running and that HERMES_API_URL points to it.'
			};
		case 'upstream_error':
		case 'invalid_response':
			return {
				titleKey: 'Hermes Agent returned an unexpected response',
				descriptionKey: 'The engine answered, but Open WebUI could not read the result.',
				hintKey: 'Check the Hermes Agent logs and confirm both versions are compatible.'
			};
		case 'request_failed':
			return {
				titleKey: 'Engine status could not be retrieved',
				descriptionKey: 'Open WebUI could not complete the request. Your session may have expired.',
				hintKey: 'Reload the page, then sign in again if the problem persists.'
			};
		case 'degraded':
			return {
				titleKey: 'Hermes Agent is degraded',
				descriptionKey: components.length
					? 'Affected components: {{components}}'
					: 'The engine is running, but at least one component is not healthy.',
				descriptionParams: components.length ? { components: components.join(', ') } : undefined,
				hintKey: 'Open the technical details below to identify the cause.'
			};
		default:
			return {
				titleKey: 'Hermes Agent needs attention',
				descriptionKey: 'Hermes Agent needs attention. Check the service connection and try again.'
			};
	}
};

/**
 * Alertes à mettre en avant, triées par gravité.
 *
 * Anti-empilement : quand le moteur lui-même est injoignable, on renvoie UNE alerte chapeau
 * plutôt qu'une cascade de « composant indisponible » qui découlent tous de la même cause.
 *
 * Un composant `unknown` ne produit aucune alerte : on ne signale que ce que l'on sait.
 */
export const deriveAlerts = (
	status: HermesStatus | null,
	rows: HealthRow[],
	platforms: PlatformRow[] = []
): EngineAlert[] => {
	const engine = engineState(status);
	if (engine === 'unknown') return [];

	if (engine === 'down') {
		const issue = deriveIssue(status?.state);
		return [{ severity: 'critical', messageKey: issue.titleKey, hintKey: issue.hintKey }];
	}

	const alerts: EngineAlert[] = [];

	for (const row of rows) {
		if (row.overall) continue;
		if (row.state === 'down') {
			alerts.push({
				severity: 'critical',
				messageKey: '{{component}} is unavailable',
				componentKey: row.labelKey,
				href: RESOLUTION_PAGES[row.labelKey]
			});
		} else if (row.state === 'warning') {
			alerts.push({
				severity: 'warning',
				messageKey: '{{component}} needs attention',
				componentKey: row.labelKey,
				href: RESOLUTION_PAGES[row.labelKey]
			});
		}
	}

	// Une plateforme déconnectée n'empêche pas le moteur de tourner : c'est une information,
	// pas une panne. On ne la remonte que si d'autres sont bien connectées — sinon la ligne
	// « passerelle » a déjà tout dit et on empilerait deux fois la même chose.
	const disconnected = platforms.filter((platform) => platform.state === 'down').length;
	const connected = platforms.filter((platform) => platform.state === 'ok').length;
	if (disconnected > 0 && connected > 0) {
		alerts.push({
			severity: 'info',
			messageKey: '{{count}} platform disconnected',
			messageParams: { count: disconnected }
		});
	}

	const rank: Record<AlertSeverity, number> = { critical: 0, warning: 1, info: 2 };
	return alerts.sort((a, b) => rank[a.severity] - rank[b.severity]);
};

/** Extrait une liste d'éléments quel que soit le nom de l'enveloppe renvoyée par Hermes. */
export const listFrom = (
	value: Record<string, unknown> | null,
	keys: string[]
): Record<string, unknown>[] => {
	if (!value) return [];
	for (const key of keys) {
		if (Array.isArray(value[key])) return value[key] as Record<string, unknown>[];
	}
	return [];
};
