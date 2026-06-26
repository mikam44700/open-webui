// Logique pure de la page Automatisations (feature 013) — testable hors composant.
// Le mapping rythme→schedule définitif est côté bridge (source de vérité Hermes) ;
// ici on construit le payload « rythme » envoyé au bridge et on présente les états.

export type AutomationStatus = 'active' | 'paused' | 'done' | 'error';

const STATUS_INFO: Record<AutomationStatus, { label: string; cls: string }> = {
	active: { label: 'Active', cls: 'text-green-700 bg-green-50 dark:text-green-400 dark:bg-green-900/20' },
	paused: { label: 'En pause', cls: 'text-gray-600 bg-gray-100 dark:text-gray-300 dark:bg-gray-800' },
	done: { label: 'Terminée', cls: 'text-blue-700 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20' },
	error: { label: 'En erreur', cls: 'text-amber-700 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20' }
};

export const statusInfo = (status: string): { label: string; cls: string } =>
	STATUS_INFO[status as AutomationStatus] ?? { label: status, cls: '' };

export type RhythmForm = {
	rhythmType: 'daily' | 'weekly' | 'interval' | 'once' | 'advanced';
	time?: string;
	weekday?: number;
	everyValue?: number;
	everyUnit?: 'h' | 'm';
	onceAt?: string;
	advancedSchedule?: string;
};

// Construit le payload « rhythm » (preset dirigeant) attendu par le bridge.
export const buildRhythm = (f: RhythmForm): Record<string, unknown> => {
	switch (f.rhythmType) {
		case 'daily':
			return { type: 'daily', time: f.time };
		case 'weekly':
			return { type: 'weekly', weekday: f.weekday, time: f.time };
		case 'interval':
			return {
				type: 'interval',
				every_minutes: (f.everyUnit ?? 'h') === 'h' ? (f.everyValue ?? 1) * 60 : (f.everyValue ?? 1)
			};
		case 'once':
			return { type: 'once', at: f.onceAt };
		case 'advanced':
			return { type: 'advanced', schedule: f.advancedSchedule };
	}
};
