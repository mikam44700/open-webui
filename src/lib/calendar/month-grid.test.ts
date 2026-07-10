import { describe, it, expect } from 'vitest';
import {
	dayKey,
	parseLocal,
	buildMonthMatrix,
	bucketEventsByDay,
	visibleRange,
	WEEKDAY_LABELS
} from './month-grid';

describe('dayKey', () => {
	it('formate en YYYY-MM-DD local avec zéros', () => {
		expect(dayKey(new Date(2026, 6, 5))).toBe('2026-07-05');
	});
});

describe('parseLocal', () => {
	it('journée entière (date seule) → minuit local', () => {
		const d = parseLocal('2026-07-15')!;
		expect(d.getFullYear()).toBe(2026);
		expect(d.getMonth()).toBe(6);
		expect(d.getDate()).toBe(15);
		expect(d.getHours()).toBe(0);
	});
	it('horodaté → conserve l’heure locale', () => {
		const d = parseLocal('2026-07-15T14:30:00')!;
		expect(d.getHours()).toBe(14);
		expect(d.getMinutes()).toBe(30);
	});
	it('vide → null', () => {
		expect(parseLocal('')).toBeNull();
	});
});

describe('buildMonthMatrix', () => {
	it('produit 6 semaines de 7 jours', () => {
		const m = buildMonthMatrix(2026, 6);
		expect(m).toHaveLength(6);
		m.forEach((w) => expect(w).toHaveLength(7));
	});

	it('juillet 2026 commence le lundi 29 juin (semaine lundi)', () => {
		// 1er juillet 2026 = mercredi → la grille démarre lundi 29 juin.
		const m = buildMonthMatrix(2026, 6);
		expect(m[0][0].key).toBe('2026-06-29');
		expect(m[0][0].inMonth).toBe(false);
		// Le mercredi de la 1re ligne = 1er juillet, dans le mois.
		expect(m[0][2].key).toBe('2026-07-01');
		expect(m[0][2].inMonth).toBe(true);
	});

	it('marque le jour courant via today injecté', () => {
		const today = new Date(2026, 6, 15);
		const m = buildMonthMatrix(2026, 6, today);
		const flat = m.flat();
		const todays = flat.filter((c) => c.isToday);
		expect(todays).toHaveLength(1);
		expect(todays[0].key).toBe('2026-07-15');
	});

	it('7 libellés de jours, lundi en tête', () => {
		expect(WEEKDAY_LABELS).toHaveLength(7);
		expect(WEEKDAY_LABELS[0]).toBe('Lun');
		expect(WEEKDAY_LABELS[6]).toBe('Dim');
	});
});

describe('bucketEventsByDay', () => {
	it('place un événement horodaté sur son jour', () => {
		const map = bucketEventsByDay([{ start: '2026-07-15T14:00:00', end: '2026-07-15T15:00:00' }]);
		expect(map['2026-07-15']).toHaveLength(1);
	});

	it('journée entière (fin exclusive) reste sur le seul jour', () => {
		// Google : all-day du 15 → end = 16 (exclusif). Ne doit PAS déborder sur le 16.
		const map = bucketEventsByDay([{ start: '2026-07-15', end: '2026-07-16' }]);
		expect(map['2026-07-15']).toHaveLength(1);
		expect(map['2026-07-16']).toBeUndefined();
	});

	it('événement horodaté sur plusieurs jours couvre chaque jour', () => {
		const map = bucketEventsByDay([{ start: '2026-07-15T10:00:00', end: '2026-07-17T12:00:00' }]);
		expect(map['2026-07-15']).toHaveLength(1);
		expect(map['2026-07-16']).toHaveLength(1);
		expect(map['2026-07-17']).toHaveLength(1);
	});

	it('ignore un début invalide', () => {
		expect(Object.keys(bucketEventsByDay([{ start: '' }]))).toHaveLength(0);
	});
});

describe('visibleRange', () => {
	it('couvre 42 jours et démarre au 1er jour de la grille', () => {
		const { start, end } = visibleRange(2026, 6);
		const s = new Date(start);
		const e = new Date(end);
		const days = Math.round((e.getTime() - s.getTime()) / (24 * 3600 * 1000));
		expect(days).toBe(42);
	});
});
