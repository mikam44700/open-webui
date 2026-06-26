import { describe, it, expect } from 'vitest';
import { toIso, validateEventForm } from './event-form';

describe('toIso', () => {
	it('ajoute les secondes à une valeur datetime-local', () => {
		expect(toIso('2026-06-28T12:00')).toBe('2026-06-28T12:00:00');
	});
	it('laisse une valeur déjà complète', () => {
		expect(toIso('2026-06-28T12:00:00')).toBe('2026-06-28T12:00:00');
	});
	it('vide -> vide', () => {
		expect(toIso('')).toBe('');
	});
});

describe('validateEventForm', () => {
	const base = { title: 'Réunion', startLocal: '2026-06-28T12:00', endLocal: '2026-06-28T13:00' };

	it('valide un événement correct et construit le body', () => {
		const r = validateEventForm(base);
		expect(r.ok).toBe(true);
		if (r.ok) {
			expect(r.body.title).toBe('Réunion');
			expect(r.body.start).toBe('2026-06-28T12:00:00');
			expect(r.body.end).toBe('2026-06-28T13:00:00');
		}
	});

	it('inclut le lieu si fourni', () => {
		const r = validateEventForm({ ...base, location: ' Bureau ' });
		expect(r.ok && r.body.location).toBe('Bureau');
	});

	it('refuse un titre vide', () => {
		expect(validateEventForm({ ...base, title: '  ' }).ok).toBe(false);
	});

	it('refuse une fin avant le début', () => {
		const r = validateEventForm({ ...base, endLocal: '2026-06-28T11:00' });
		expect(r.ok).toBe(false);
	});

	it('refuse des dates manquantes', () => {
		expect(validateEventForm({ ...base, startLocal: '' }).ok).toBe(false);
	});
});
