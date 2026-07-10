// Logique pure de la grille « mois » du Calendrier (Agent OS).
// Alimentée par les événements normalisés d'Hermes (start/end ISO exprimés dans le
// fuseau local, all_day déduit de l'absence d'heure). Aucune dépendance à Svelte :
// tout est testable unitairement.

export type DayCell = {
	date: Date; // minuit local du jour
	key: string; // « YYYY-MM-DD »
	inMonth: boolean; // appartient au mois affiché (vs jours débordants gris)
	isToday: boolean;
};

export type DatedEvent = { start: string; end?: string };

/** Clé stable d'un jour en heure locale : « YYYY-MM-DD » (jamais d'UTC, pas de décalage). */
export const dayKey = (d: Date): string => {
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${y}-${m}-${day}`;
};

/**
 * Parse un début/fin d'événement en Date locale.
 * - « 2026-07-15 » (journée entière) → minuit local du 15 (et non UTC, qui décalerait).
 * - « 2026-07-15T14:00:00 » (horodaté) → interprété en heure locale par le moteur JS.
 */
export const parseLocal = (iso: string): Date | null => {
	if (!iso) return null;
	if (!iso.includes('T')) {
		const [y, m, d] = iso.split('-').map(Number);
		if (!y || !m || !d) return null;
		return new Date(y, m - 1, d);
	}
	const dt = new Date(iso);
	return isNaN(dt.getTime()) ? null : dt;
};

/** Minuit local d'une date (copie, sans muter l'entrée). */
const midnight = (d: Date): Date => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/**
 * Matrice 6×7 (42 cellules) du mois donné, semaines commençant le LUNDI.
 * Inclut les jours débordants des mois voisins pour remplir la grille.
 * `today` est injectable pour des tests déterministes (défaut : maintenant).
 */
export const buildMonthMatrix = (year: number, month: number, today: Date = new Date()): DayCell[][] => {
	const first = new Date(year, month, 1);
	const offset = (first.getDay() + 6) % 7; // Lun=0 … Dim=6
	const start = new Date(year, month, 1 - offset);
	const todayKey = dayKey(today);

	const weeks: DayCell[][] = [];
	for (let w = 0; w < 6; w++) {
		const row: DayCell[] = [];
		for (let d = 0; d < 7; d++) {
			const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + w * 7 + d);
			const key = dayKey(date);
			row.push({ date, key, inMonth: date.getMonth() === month, isToday: key === todayKey });
		}
		weeks.push(row);
	}
	return weeks;
};

/**
 * Regroupe les événements par jour (clé « YYYY-MM-DD »). Un événement sur plusieurs
 * jours apparaît sur chaque jour couvert. Pour une journée entière, la fin Google est
 * exclusive (jour suivant) : on retire donc le dernier jour.
 */
export const bucketEventsByDay = <T extends DatedEvent>(events: T[]): Record<string, T[]> => {
	const map: Record<string, T[]> = {};
	for (const e of events) {
		const startDate = parseLocal(e.start);
		if (!startDate) continue;
		const allDay = !e.start.includes('T');
		const endParsed = e.end ? parseLocal(e.end) : null;
		let last = endParsed ? midnight(endParsed) : midnight(startDate);
		// Fin « journée entière » exclusive → recule d'un jour (sans passer avant le début).
		if (allDay && e.end && !e.end.includes('T')) {
			const prev = new Date(last.getFullYear(), last.getMonth(), last.getDate() - 1);
			if (prev.getTime() >= midnight(startDate).getTime()) last = prev;
		}
		const cursor = midnight(startDate);
		while (cursor.getTime() <= last.getTime()) {
			const key = dayKey(cursor);
			(map[key] ??= []).push(e);
			cursor.setDate(cursor.getDate() + 1);
		}
	}
	return map;
};

/**
 * Fenêtre de dates (ISO UTC) couvrant toute la grille 6 semaines affichée, pour
 * charger les événements du mois visible (jours débordants inclus).
 */
export const visibleRange = (year: number, month: number): { start: string; end: string } => {
	const first = new Date(year, month, 1);
	const offset = (first.getDay() + 6) % 7;
	const start = new Date(year, month, 1 - offset);
	const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 42);
	return { start: start.toISOString(), end: end.toISOString() };
};

/** Libellé FR du mois, ex. « juillet 2026 ». */
export const monthLabel = (year: number, month: number): string =>
	new Date(year, month, 1).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

/** Noms courts des jours, semaine commençant le lundi. */
export const WEEKDAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
