// Helpers partagés de la page Agents (avatar placeholder + nom d'affichage).

// Couleur stable dérivée du nom (avatar placeholder en attendant les illustrations 3D).
const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#ef4444'];

// Dégradés assortis (du clair vers la teinte) pour des avatars premium, alignés sur COLORS.
const GRADIENTS: [string, string][] = [
	['#818cf8', '#4f46e5'],
	['#a78bfa', '#7c3aed'],
	['#f472b6', '#db2777'],
	['#fbbf24', '#d97706'],
	['#34d399', '#059669'],
	['#22d3ee', '#0891b2'],
	['#fb7185', '#e11d48']
];

const indexFor = (name: string): number => {
	let h = 0;
	for (let i = 0; i < (name?.length ?? 0); i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
	return h % COLORS.length;
};

export const colorFor = (name: string): string => COLORS[indexFor(name)];

// Dégradé CSS stable dérivé du nom (avatar premium).
export const gradientFor = (name: string): string => {
	const [from, to] = GRADIENTS[indexFor(name)];
	return `linear-gradient(135deg, ${from}, ${to})`;
};

export const initial = (name: string): string => (name?.[0] ?? '?').toUpperCase();

// « assistant-rh » -> « Assistant Rh » (affichage lisible d'un identifiant de profil).
export const prettifyName = (name: string): string =>
	(name ?? '')
		.replace(/[-_]+/g, ' ')
		.trim()
		.replace(/\b\w/g, (c) => c.toUpperCase());
