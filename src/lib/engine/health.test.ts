import { describe, expect, it } from 'vitest';

import {
	buildActivity,
	buildHealthRows,
	buildPlatformRows,
	checkState,
	deriveAlerts,
	deriveIssue,
	engineState,
	failingComponents,
	groupCapabilities,
	listFrom,
	type HealthRow
} from './health';
import type { HermesStatus } from '$lib/apis/hermes';

const bytes = (n: number) => `${n} B`;

const operational: HermesStatus = {
	configured: true,
	state: 'operational',
	version: '1.4.0',
	model: 'claude-sonnet-5',
	active_agents: 2,
	gateway_state: 'running',
	gateway_busy: false,
	platforms: {
		whatsapp: { state: 'connected' },
		signal: { state: 'disconnected' }
	},
	readiness: {
		status: 'ok',
		checks: {
			state_db: { status: 'ok' },
			config: { status: 'ok' },
			model: { status: 'ok' },
			disk: { status: 'ok', used_percent: 42.5, free_bytes: 1024 },
			gateway: { status: 'ok', state: 'running', connected_platforms: 1, platforms: 2 },
			background_queues: {
				status: 'ok',
				active_api_runs: 3,
				active_delegations: 1,
				process_completions: 0
			}
		}
	}
};

const rowFor = (rows: HealthRow[], labelKey: string) =>
	rows.find((row) => row.labelKey === labelKey);

describe('checkState', () => {
	it('reconnait les etats sains', () => {
		for (const value of ['ok', 'ready', 'healthy', 'running', 'connected']) {
			expect(checkState({ status: value })).toBe('ok');
		}
	});

	it('reconnait les etats degrades et en panne', () => {
		expect(checkState({ status: 'degraded' })).toBe('warning');
		expect(checkState({ status: 'stopped' })).toBe('down');
	});

	it('accepte indifferemment status et state', () => {
		expect(checkState({ state: 'RUNNING' })).toBe('ok');
	});

	it('ne transforme jamais un mot inconnu ou absent en panne', () => {
		expect(checkState({ status: 'wat' })).toBe('unknown');
		expect(checkState(undefined)).toBe('unknown');
		expect(checkState({})).toBe('unknown');
	});
});

describe('engineState', () => {
	it('mappe les etats du proxy', () => {
		expect(engineState(operational)).toBe('ok');
		expect(engineState({ ...operational, state: 'degraded' })).toBe('warning');
		expect(engineState({ ...operational, state: 'unavailable' })).toBe('down');
	});

	it('reste inconnu quand aucun etat n est fourni', () => {
		expect(engineState(null)).toBe('unknown');
		expect(engineState({ ...operational, state: '' })).toBe('unknown');
	});
});

describe('buildHealthRows', () => {
	it('expose les six sondes quand Hermes les rapporte', () => {
		const rows = buildHealthRows(operational, bytes);
		expect(rows.map((row) => row.labelKey)).toEqual([
			'Engine',
			'AI model',
			'Messaging',
			'Working memory',
			'Settings',
			'Storage space'
		]);
	});

	it('affiche le remplissage du disque et l espace libre formate', () => {
		const disk = rowFor(buildHealthRows(operational, bytes), 'Storage space');
		expect(disk?.detailKey).toBe('{{percent}}% used, {{free}} free');
		expect(disk?.detailParams).toEqual({ percent: 42.5, free: '1024 B' });
	});

	it('omet l espace libre quand Hermes ne le rapporte pas', () => {
		const noFree: HermesStatus = {
			...operational,
			readiness: { checks: { disk: { status: 'ok', used_percent: 12 } } }
		};
		const disk = rowFor(buildHealthRows(noFree, bytes), 'Storage space');
		expect(disk?.detailKey).toBe('{{percent}}% used');
		expect(disk?.detailParams).toEqual({ percent: 12 });
	});

	it('resume les plateformes connectees sur la ligne passerelle', () => {
		const gateway = rowFor(buildHealthRows(operational, bytes), 'Messaging');
		expect(gateway?.detailKey).toBe('{{connected}} of {{total}} connected');
		expect(gateway?.detailParams).toEqual({ connected: 1, total: 2 });
	});

	it('marque le moteur comme etat global et porte sa version', () => {
		const engine = rowFor(buildHealthRows(operational, bytes), 'Engine');
		expect(engine?.overall).toBe(true);
		expect(engine?.detail).toBe('v1.4.0');
	});

	it('ne garde que le moteur quand aucune sonde n est disponible', () => {
		const rows = buildHealthRows({ ...operational, readiness: {} }, bytes);
		expect(rows).toHaveLength(1);
		expect(rows[0].labelKey).toBe('Engine');
	});

	it('masque une sonde absente plutot que d afficher une ligne inconnue', () => {
		const partial: HermesStatus = {
			...operational,
			readiness: { checks: { state_db: { status: 'ok' } } }
		};
		const labels = buildHealthRows(partial, bytes).map((row) => row.labelKey);
		expect(labels).toEqual(['Engine', 'Working memory']);
	});
});

describe('failingComponents', () => {
	it('liste les composants en defaut sans compter le moteur lui-meme', () => {
		const degraded: HermesStatus = {
			...operational,
			state: 'degraded',
			readiness: {
				checks: {
					...(operational.readiness?.checks as Record<string, unknown>),
					gateway: { status: 'degraded', state: 'stopped', connected_platforms: 0, platforms: 2 },
					disk: { status: 'degraded', used_percent: 96, free_bytes: 10 }
				}
			}
		};
		expect(failingComponents(buildHealthRows(degraded, bytes))).toEqual([
			'Messaging',
			'Storage space'
		]);
	});

	it('ne signale rien quand tout va bien', () => {
		expect(failingComponents(buildHealthRows(operational, bytes))).toEqual([]);
	});
});

describe('buildPlatformRows', () => {
	it('trie les plateformes et traduit leur etat', () => {
		expect(buildPlatformRows(operational)).toEqual([
			{ name: 'signal', state: 'down' },
			{ name: 'whatsapp', state: 'ok' }
		]);
	});

	it('renvoie une liste vide quand aucune plateforme n est declaree', () => {
		expect(buildPlatformRows({ ...operational, platforms: undefined })).toEqual([]);
		expect(buildPlatformRows(null)).toEqual([]);
	});
});

describe('buildActivity', () => {
	it('lit les compteurs de la file de fond', () => {
		expect(buildActivity(operational)).toEqual({
			activeAgents: 2,
			apiRuns: 3,
			delegations: 1,
			pendingCompletions: 0
		});
	});

	it('ramene a zero les valeurs absentes ou negatives', () => {
		expect(buildActivity(null)).toEqual({
			activeAgents: 0,
			apiRuns: 0,
			delegations: 0,
			pendingCompletions: 0
		});
		expect(buildActivity({ ...operational, active_agents: -5, readiness: {} }).activeAgents).toBe(
			0
		);
	});
});

describe('groupCapabilities', () => {
	const features = {
		chat_completions: true,
		run_stop: true,
		session_fork: false,
		admin_config_rw: false,
		cors: true,
		session_continuity_header: 'X-Hermes-Session-Id'
	};

	it('regroupe par famille', () => {
		const groups = groupCapabilities(features);
		expect(groups.map((g) => g.titleKey)).toEqual([
			'Conversation',
			'Executions',
			'Sessions',
			'Administration',
			'Other capabilities'
		]);
	});

	it('conserve les capacites desactivees', () => {
		const admin = groupCapabilities(features).find((g) => g.titleKey === 'Administration');
		expect(admin?.items).toEqual([{ name: 'admin_config_rw', enabled: false }]);
	});

	it('ecarte les valeurs non booleennes, qui ne sont pas des capacites', () => {
		const names = groupCapabilities(features).flatMap((g) => g.items.map((i) => i.name));
		expect(names).not.toContain('session_continuity_header');
		expect(names).toContain('cors');
	});

	it('renvoie une liste vide sans capacites', () => {
		expect(groupCapabilities(undefined)).toEqual([]);
	});
});

describe('deriveIssue', () => {
	it('donne une cause et un conseil distincts par type de panne', () => {
		const causes = [
			'not_configured',
			'authentication_failed',
			'unavailable',
			'upstream_error',
			'request_failed'
		];
		const titles = causes.map((cause) => deriveIssue(cause).titleKey);
		expect(new Set(titles).size).toBe(causes.length);
		for (const cause of causes) {
			expect(deriveIssue(cause).hintKey).toBeTruthy();
		}
	});

	it('nomme les composants en cause quand le moteur est degrade', () => {
		const issue = deriveIssue('degraded', ['Passerelle', 'Espace disque']);
		expect(issue.descriptionKey).toBe('Affected components: {{components}}');
		expect(issue.descriptionParams).toEqual({ components: 'Passerelle, Espace disque' });
	});

	it('reste generique quand le composant fautif est inconnu', () => {
		const issue = deriveIssue('degraded');
		expect(issue.descriptionKey).toBe(
			'The engine is running, but at least one component is not healthy.'
		);
		expect(issue.descriptionParams).toBeUndefined();
	});

	it('retombe sur un message neutre pour un etat inattendu', () => {
		expect(deriveIssue('quelque_chose_de_nouveau').titleKey).toBe('Hermes Agent needs attention');
		expect(deriveIssue(undefined).titleKey).toBe('Hermes Agent needs attention');
	});
});

describe('deriveAlerts', () => {
	const rowsOf = (status: HermesStatus) => buildHealthRows(status, bytes);

	it('ne signale rien quand tout est operationnel et toutes les plateformes connectees', () => {
		expect(
			deriveAlerts(operational, rowsOf(operational), [{ name: 'whatsapp', state: 'ok' }])
		).toEqual([]);
	});

	it('moteur injoignable : une seule alerte chapeau, pas une cascade', () => {
		const down: HermesStatus = { ...operational, state: 'unavailable' };
		const alerts = deriveAlerts(down, rowsOf(down), buildPlatformRows(down));
		expect(alerts).toHaveLength(1);
		expect(alerts[0].severity).toBe('critical');
		expect(alerts[0].messageKey).toBe('Hermes Agent is unreachable');
		expect(alerts[0].hintKey).toBeTruthy();
	});

	it('signale chaque composant en defaut avec la bonne gravite', () => {
		const degraded: HermesStatus = {
			...operational,
			state: 'degraded',
			readiness: {
				checks: {
					state_db: { status: 'stopped' },
					disk: { status: 'degraded', used_percent: 96 }
				}
			}
		};
		const alerts = deriveAlerts(degraded, rowsOf(degraded), []);
		expect(alerts).toEqual([
			{
				severity: 'critical',
				messageKey: '{{component}} is unavailable',
				componentKey: 'Working memory'
			},
			{
				severity: 'warning',
				messageKey: '{{component}} needs attention',
				componentKey: 'Storage space'
			}
		]);
	});

	it('ne produit aucune alerte pour un composant inconnu', () => {
		const partial: HermesStatus = {
			...operational,
			readiness: { checks: { state_db: { status: 'mystere' } } }
		};
		expect(deriveAlerts(partial, rowsOf(partial), [])).toEqual([]);
	});

	it('signale les plateformes deconnectees seulement si d autres sont connectees', () => {
		const rows = rowsOf(operational);
		const mixed = deriveAlerts(operational, rows, [
			{ name: 'whatsapp', state: 'ok' },
			{ name: 'signal', state: 'down' }
		]);
		expect(mixed).toEqual([
			{
				severity: 'info',
				messageKey: '{{count}} platform disconnected',
				messageParams: { count: 1 }
			}
		]);

		const allDown = deriveAlerts(operational, rows, [{ name: 'signal', state: 'down' }]);
		expect(allDown).toEqual([]);
	});

	it('reste silencieux tant que l etat du moteur est inconnu', () => {
		expect(deriveAlerts(null, [], [])).toEqual([]);
	});
});

describe('listFrom', () => {
	it('trouve la premiere cle contenant un tableau', () => {
		expect(listFrom({ items: [{ id: 'a' }] }, ['data', 'items'])).toEqual([{ id: 'a' }]);
	});

	it('renvoie une liste vide sans correspondance', () => {
		expect(listFrom({ data: 'nope' }, ['data'])).toEqual([]);
		expect(listFrom(null, ['data'])).toEqual([]);
	});
});

describe('alertes cliquables', () => {
	it('pointe vers la page de resolution quand elle existe', () => {
		const noModel: HermesStatus = {
			...operational,
			state: 'degraded',
			readiness: { checks: { model: { status: 'degraded' } } }
		};
		const alerts = deriveAlerts(noModel, buildHealthRows(noModel, bytes), []);
		expect(alerts[0].href).toBe('/workspace/models');
	});

	it('laisse un conseil plutot qu un lien mort quand aucune page ne resout', () => {
		const noDisk: HermesStatus = {
			...operational,
			state: 'degraded',
			readiness: { checks: { disk: { status: 'degraded', used_percent: 97 } } }
		};
		const alerts = deriveAlerts(noDisk, buildHealthRows(noDisk, bytes), []);
		expect(alerts[0].href).toBeUndefined();
	});

	it('le moteur injoignable donne toujours une action a mener', () => {
		const down: HermesStatus = { ...operational, state: 'not_configured' };
		const [alert] = deriveAlerts(down, buildHealthRows(down, bytes), []);
		expect(alert.hintKey).toBeTruthy();
	});
});
