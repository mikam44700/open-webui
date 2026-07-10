import { describe, it, expect } from 'vitest';
import { layoutDayEvents } from './day-layout';

const day = new Date(2026, 6, 10); // 10 juillet 2026

describe('layoutDayEvents', () => {
	it('positionne un événement horodaté en minutes depuis minuit', () => {
		const r = layoutDayEvents([{ start: '2026-07-10T09:00:00', end: '2026-07-10T10:00:00' }], day);
		expect(r).toHaveLength(1);
		expect(r[0].startMin).toBe(540); // 9 h
		expect(r[0].endMin).toBe(600); // 10 h
		expect(r[0].lanes).toBe(1);
		expect(r[0].lane).toBe(0);
	});

	it('ignore les journées entières (pas de T)', () => {
		expect(layoutDayEvents([{ start: '2026-07-10', end: '2026-07-11' }], day)).toHaveLength(0);
	});

	it('deux événements qui se chevauchent → 2 colonnes distinctes', () => {
		const r = layoutDayEvents(
			[
				{ start: '2026-07-10T09:00:00', end: '2026-07-10T10:30:00' },
				{ start: '2026-07-10T09:30:00', end: '2026-07-10T11:00:00' }
			],
			day
		);
		expect(r.every((x) => x.lanes === 2)).toBe(true);
		expect(new Set(r.map((x) => x.lane)).size).toBe(2);
	});

	it('deux événements disjoints → 1 colonne chacun', () => {
		const r = layoutDayEvents(
			[
				{ start: '2026-07-10T09:00:00', end: '2026-07-10T10:00:00' },
				{ start: '2026-07-10T11:00:00', end: '2026-07-10T12:00:00' }
			],
			day
		);
		expect(r.every((x) => x.lanes === 1)).toBe(true);
	});

	it('événement de la veille qui déborde → borné à minuit', () => {
		const r = layoutDayEvents([{ start: '2026-07-09T23:00:00', end: '2026-07-10T01:00:00' }], day);
		expect(r).toHaveLength(1);
		expect(r[0].startMin).toBe(0);
		expect(r[0].endMin).toBe(60);
	});

	it('durée par défaut si fin absente', () => {
		const r = layoutDayEvents([{ start: '2026-07-10T09:00:00' }], day);
		expect(r[0].endMin).toBe(570); // 9 h + 30 min
	});
});
