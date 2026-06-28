// Logique pure de la page Calendrier (feature 014) — testable hors composant.

export type EventForm = {
	title: string;
	startLocal: string; // valeur d'un <input type="datetime-local"> : "2026-06-28T12:00"
	endLocal: string;
	location?: string;
};

// Normalise une valeur datetime-local en ISO 8601 avec les secondes (le fuseau est ajouté
// côté script google_api.py). "2026-06-28T12:00" -> "2026-06-28T12:00:00".
export const toIso = (datetimeLocal: string): string => {
	if (!datetimeLocal) return '';
	return datetimeLocal.length === 16 ? `${datetimeLocal}:00` : datetimeLocal;
};

export type EventValidation = { ok: true; body: Record<string, string> } | { ok: false; error: string };

export const validateEventForm = (f: EventForm): EventValidation => {
	if (!f.title.trim()) return { ok: false, error: 'Donnez un titre à l’événement.' };
	if (!f.startLocal || !f.endLocal) return { ok: false, error: 'Indiquez le début et la fin.' };
	if (toIso(f.endLocal) <= toIso(f.startLocal))
		return { ok: false, error: 'La fin doit être après le début.' };
	const body: Record<string, string> = {
		title: f.title.trim(),
		start: toIso(f.startLocal),
		end: toIso(f.endLocal)
	};
	if (f.location?.trim()) body.location = f.location.trim();
	return { ok: true, body };
};
