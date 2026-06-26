import { describe, it, expect } from 'vitest';
import { statusInfo, buildRhythm } from './labels';

describe('statusInfo', () => {
	it('mappe les 4 statuts vers un libellé français', () => {
		expect(statusInfo('active').label).toBe('Active');
		expect(statusInfo('paused').label).toBe('En pause');
		expect(statusInfo('done').label).toBe('Terminée');
		expect(statusInfo('error').label).toBe('En erreur');
	});

	it('retombe sur le statut brut si inconnu (jamais de crash)', () => {
		expect(statusInfo('mystère').label).toBe('mystère');
		expect(statusInfo('mystère').cls).toBe('');
	});
});

describe('buildRhythm', () => {
	it('daily → time', () => {
		expect(buildRhythm({ rhythmType: 'daily', time: '08:00' })).toEqual({ type: 'daily', time: '08:00' });
	});

	it('weekly → weekday + time', () => {
		expect(buildRhythm({ rhythmType: 'weekly', weekday: 0, time: '09:00' })).toEqual({
			type: 'weekly',
			weekday: 0,
			time: '09:00'
		});
	});

	it('interval en heures → every_minutes converti', () => {
		expect(buildRhythm({ rhythmType: 'interval', everyValue: 2, everyUnit: 'h' })).toEqual({
			type: 'interval',
			every_minutes: 120
		});
	});

	it('interval en minutes → every_minutes brut', () => {
		expect(buildRhythm({ rhythmType: 'interval', everyValue: 30, everyUnit: 'm' })).toEqual({
			type: 'interval',
			every_minutes: 30
		});
	});

	it('once → at', () => {
		expect(buildRhythm({ rhythmType: 'once', onceAt: '2026-07-01T14:00' })).toEqual({
			type: 'once',
			at: '2026-07-01T14:00'
		});
	});

	it('advanced → schedule brut', () => {
		expect(buildRhythm({ rhythmType: 'advanced', advancedSchedule: '0 9 * * 1-5' })).toEqual({
			type: 'advanced',
			schedule: '0 9 * * 1-5'
		});
	});
});
