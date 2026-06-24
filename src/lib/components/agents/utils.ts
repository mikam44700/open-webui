// Helpers partagés de la page Agents (avatar placeholder + nom d'affichage).

// Couleur stable dérivée du nom (avatar placeholder en attendant les illustrations 3D).
const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#ef4444'];

export const colorFor = (name: string): string => {
	let h = 0;
	for (let i = 0; i < (name?.length ?? 0); i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
	return COLORS[h % COLORS.length];
};

export const initial = (name: string): string => (name?.[0] ?? '?').toUpperCase();

// « assistant-rh » -> « Assistant Rh » (affichage lisible d'un identifiant de profil).
export const prettifyName = (name: string): string =>
	(name ?? '')
		.replace(/[-_]+/g, ' ')
		.trim()
		.replace(/\b\w/g, (c) => c.toUpperCase());
