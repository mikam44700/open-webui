// Logique pure des vues du Calendrier (Jour / Semaine / Mois) : navigation, fenêtre
// de chargement et libellés. Sans dépendance à Svelte, entièrement testable.

import { visibleRange, monthLabel } from './month-grid';

export type ViewMode = 'day' | 'week' | 'month';

/** Minuit local d'une date (copie). */
const midnight = (d: Date): Date => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/** Lundi (minuit local) de la semaine contenant `d`. */
export const startOfWeek = (d: Date): Date => {
	const offset = (d.getDay() + 6) % 7; // Lun=0 … Dim=6
	return new Date(d.getFullYear(), d.getMonth(), d.getDate() - offset);
};

/** Les 7 jours (minuit local) de la semaine contenant `d`, du lundi au dimanche. */
export const weekDays = (d: Date): Date[] => {
	const start = startOfWeek(d);
	return Array.from({ length: 7 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
};

/** Fenêtre de dates (ISO UTC) à charger pour la vue courante. */
export const rangeFor = (mode: ViewMode, anchor: Date): { start: string; end: string } => {
	if (mode === 'month') return visibleRange(anchor.getFullYear(), anchor.getMonth());
	if (mode === 'week') {
		const start = startOfWeek(anchor);
		const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 7);
		return { start: start.toISOString(), end: end.toISOString() };
	}
	const start = midnight(anchor);
	const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 1);
	return { start: start.toISOString(), end: end.toISOString() };
};

/** Décale l'ancre d'une unité de la vue (mois / semaine / jour) dans le sens `dir` (-1 | 1). */
export const shiftAnchor = (mode: ViewMode, anchor: Date, dir: number): Date => {
	if (mode === 'month') return new Date(anchor.getFullYear(), anchor.getMonth() + dir, 1);
	const step = mode === 'week' ? 7 : 1;
	return new Date(anchor.getFullYear(), anchor.getMonth(), anchor.getDate() + dir * step);
};

const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1);

/** Libellé de l'en-tête selon la vue. */
export const titleFor = (mode: ViewMode, anchor: Date): string => {
	if (mode === 'month') return cap(monthLabel(anchor.getFullYear(), anchor.getMonth()));
	if (mode === 'day') {
		return cap(
			anchor.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
		);
	}
	// Semaine : « 6 – 12 juillet 2026 », avec mois/année dédupliqués aux bornes.
	const days = weekDays(anchor);
	const a = days[0];
	const b = days[6];
	const sameMonth = a.getMonth() === b.getMonth();
	const sameYear = a.getFullYear() === b.getFullYear();
	const left = sameMonth
		? String(a.getDate())
		: a.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', ...(sameYear ? {} : { year: 'numeric' }) });
	const right = b.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
	return `${left} – ${right}`;
};
