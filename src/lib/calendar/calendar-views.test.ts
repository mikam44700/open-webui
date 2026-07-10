import { describe, it, expect } from 'vitest';
import { startOfWeek, weekDays, rangeFor, shiftAnchor, titleFor } from './calendar-views';

describe('startOfWeek', () => {
	it('renvoie le lundi de la semaine', () => {
		// 10 juillet 2026 = vendredi → lundi 6 juillet.
		expect(startOfWeek(new Date(2026, 6, 10)).getDate()).toBe(6);
	});
	it('un lundi reste ce lundi', () => {
		expect(startOfWeek(new Date(2026, 6, 6)).getDate()).toBe(6);
	});
});

describe('weekDays', () => {
	it('7 jours du lundi au dimanche', () => {
		const days = weekDays(new Date(2026, 6, 10));
		expect(days).toHaveLength(7);
		expect(days[0].getDate()).toBe(6); // lundi
		expect(days[6].getDate()).toBe(12); // dimanche
	});
});

describe('shiftAnchor', () => {
	it('mois : +1 change de mois', () => {
		const a = shiftAnchor('month', new Date(2026, 6, 15), 1);
		expect(a.getMonth()).toBe(7);
	});
	it('semaine : +1 avance de 7 jours', () => {
		const a = shiftAnchor('week', new Date(2026, 6, 10), 1);
		expect(a.getDate()).toBe(17);
	});
	it('jour : -1 recule d’un jour', () => {
		const a = shiftAnchor('day', new Date(2026, 6, 10), -1);
		expect(a.getDate()).toBe(9);
	});
});

describe('rangeFor', () => {
	it('jour : fenêtre de 24 h', () => {
		const { start, end } = rangeFor('day', new Date(2026, 6, 10, 14));
		const h = (new Date(end).getTime() - new Date(start).getTime()) / 3600000;
		expect(h).toBe(24);
	});
	it('semaine : fenêtre de 7 jours', () => {
		const { start, end } = rangeFor('week', new Date(2026, 6, 10));
		const d = (new Date(end).getTime() - new Date(start).getTime()) / 86400000;
		expect(d).toBe(7);
	});
});

describe('titleFor', () => {
	it('mois : « Juillet 2026 »', () => {
		expect(titleFor('month', new Date(2026, 6, 1))).toBe('Juillet 2026');
	});
	it('jour : commence par le jour de la semaine capitalisé', () => {
		expect(titleFor('day', new Date(2026, 6, 10))).toMatch(/^Vendredi/);
	});
	it('semaine : intervalle avec tiret', () => {
		expect(titleFor('week', new Date(2026, 6, 10))).toContain('–');
	});
});
