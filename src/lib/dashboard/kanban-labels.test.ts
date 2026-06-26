import { describe, it, expect } from 'vitest';
import { labelForStatus, isBlockedStatus, KANBAN_STATUS_LABELS } from './kanban-labels';

describe('labelForStatus', () => {
	it('traduit les statuts connus en français', () => {
		expect(labelForStatus('running')).toBe('En cours');
		expect(labelForStatus('done')).toBe('Terminé');
		expect(labelForStatus('review')).toBe('À valider');
	});

	it('repli sur le statut brut si inconnu', () => {
		expect(labelForStatus('statut-inconnu')).toBe('statut-inconnu');
	});

	it('tous les libellés sont non vides', () => {
		for (const label of Object.values(KANBAN_STATUS_LABELS)) {
			expect(label.length).toBeGreaterThan(0);
		}
	});
});

describe('isBlockedStatus', () => {
	it('bloqué et à valider comptent comme bloqués', () => {
		expect(isBlockedStatus('blocked')).toBe(true);
		expect(isBlockedStatus('review')).toBe(true);
	});

	it('les autres statuts ne sont pas bloqués', () => {
		expect(isBlockedStatus('running')).toBe(false);
		expect(isBlockedStatus('done')).toBe(false);
	});
});
