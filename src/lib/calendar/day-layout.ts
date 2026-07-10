// Placement des événements horodatés dans une grille horaire (vues Jour / Semaine).
// Calcule, pour un jour donné, la position verticale (en minutes depuis minuit) de
// chaque événement et répartit les chevauchements en colonnes (« lanes »). Pur & testé.

import { parseLocal, type DatedEvent } from './month-grid';

export type TimedLayout<T> = {
	event: T;
	startMin: number; // minutes depuis minuit local (0–1440), borné au jour
	endMin: number; // minutes depuis minuit local, toujours > startMin
	lane: number; // colonne (0-indexée) dans le groupe de chevauchement
	lanes: number; // nombre total de colonnes du groupe
};

const DEFAULT_DURATION_MIN = 30;
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

/**
 * Place les événements horodatés d'un jour. Les entrées journée entière doivent être
 * filtrées en amont (elles ne vont pas dans la grille horaire). Multi-jours : borné au jour.
 */
export const layoutDayEvents = <T extends DatedEvent>(events: T[], day: Date): TimedLayout<T>[] => {
	const mid = new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime();
	const dayEnd = mid + 24 * 60 * 60 * 1000;

	const items = events
		.filter((e) => e.start.includes('T')) // horodatés uniquement
		.map((e) => {
			const s = parseLocal(e.start);
			if (!s) return null;
			const eRaw = e.end ? parseLocal(e.end) : null;
			const eMs = eRaw ? eRaw.getTime() : s.getTime() + DEFAULT_DURATION_MIN * 60 * 1000;
			// Ne garde que ce qui recoupe le jour.
			if (eMs <= mid || s.getTime() >= dayEnd) return null;
			const startMin = clamp((s.getTime() - mid) / 60000, 0, 1440);
			let endMin = clamp((eMs - mid) / 60000, 0, 1440);
			if (endMin <= startMin) endMin = Math.min(1440, startMin + DEFAULT_DURATION_MIN);
			return { event: e, startMin, endMin };
		})
		.filter((x): x is { event: T; startMin: number; endMin: number } => x !== null)
		.sort((a, b) => a.startMin - b.startMin || a.endMin - b.endMin);

	// Répartition en colonnes par groupe de chevauchement contigu.
	const result: TimedLayout<T>[] = [];
	let group: typeof items = [];
	let groupEnd = -1;

	const flush = () => {
		if (!group.length) return;
		const laneEnds: number[] = []; // fin (min) du dernier événement de chaque colonne
		const assigned = group.map((it) => {
			let lane = laneEnds.findIndex((end) => end <= it.startMin);
			if (lane === -1) {
				lane = laneEnds.length;
				laneEnds.push(it.endMin);
			} else {
				laneEnds[lane] = it.endMin;
			}
			return { ...it, lane };
		});
		const lanes = laneEnds.length;
		assigned.forEach((it) => result.push({ ...it, lanes }));
		group = [];
		groupEnd = -1;
	};

	for (const it of items) {
		if (group.length && it.startMin >= groupEnd) flush();
		group.push(it);
		groupEnd = Math.max(groupEnd, it.endMin);
	}
	flush();
	return result;
};
