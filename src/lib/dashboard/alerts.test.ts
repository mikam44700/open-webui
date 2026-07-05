import { describe, it, expect } from 'vitest';
import { deriveAlerts, type DashboardStates } from './alerts';

const allOk: DashboardStates = {
	bridge: 'ok',
	engine: 'ok',
	messaging: 'ok',
	memory: 'ok',
	activeBrain: true,
	blockedTasks: 0
};

describe('deriveAlerts', () => {
	it('aucune alerte quand tout est opérationnel', () => {
		expect(deriveAlerts(allOk)).toEqual([]);
	});

	it('pont injoignable => une seule alerte chapeau critique', () => {
		const alerts = deriveAlerts({ ...allOk, bridge: 'down', engine: 'unknown', messaging: 'unknown', memory: 'unknown', activeBrain: 'unknown', blockedTasks: 'unknown' });
		expect(alerts).toHaveLength(1);
		expect(alerts[0].severity).toBe('critical');
		expect(alerts[0].message).toMatch(/indisponible/i);
	});

	it('moteur en panne => alerte critique avec lien', () => {
		const alerts = deriveAlerts({ ...allOk, engine: 'down' });
		const a = alerts.find((x) => x.message.includes('Moteur'));
		expect(a).toBeDefined();
		expect(a?.severity).toBe('critical');
		expect(a?.href).toBe('/providers');
	});

	it('aucun modèle IA actif => alerte avec lien Modèles IA', () => {
		const alerts = deriveAlerts({ ...allOk, activeBrain: false });
		const a = alerts.find((x) => x.message.includes('Aucun modèle IA'));
		expect(a?.href).toBe('/providers');
	});

	it('messagerie arrêtée et mémoire inaccessible => deux alertes', () => {
		const alerts = deriveAlerts({ ...allOk, messaging: 'down', memory: 'down' });
		expect(alerts.find((x) => x.href === '/gateway')).toBeDefined();
		expect(alerts.find((x) => x.href === '/memory')).toBeDefined();
	});

	it('tâches bloquées => alerte info avec pluriel correct et lien Tâches', () => {
		expect(deriveAlerts({ ...allOk, blockedTasks: 1 }).find((x) => x.message === '1 tâche à valider')).toBeDefined();
		const a3 = deriveAlerts({ ...allOk, blockedTasks: 3 }).find((x) => x.href === '/kanban');
		expect(a3?.message).toBe('3 tâches à valider');
	});

	it('honnêteté D27 : états unknown ne génèrent aucune alerte de panne', () => {
		const alerts = deriveAlerts({
			bridge: 'ok',
			engine: 'unknown',
			messaging: 'unknown',
			memory: 'unknown',
			activeBrain: 'unknown',
			blockedTasks: 'unknown'
		});
		expect(alerts).toEqual([]);
	});
});
