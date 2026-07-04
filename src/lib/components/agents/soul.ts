// Parsing partagé de la « mission » d'un agent (SOUL.md) en sections lisibles.
// Utilisé par l'Atelier (agent généré) ET l'aperçu des agents « prêts à l'emploi »
// pour un rendu identique en cartes (Identité / Mission / Méthode / …).

export type MissionSection = { title: string; body: string; icon: string };

// Icône par section, tolérante aux accents et à la casse.
export const sectionIcon = (title: string): string => {
	const t = title
		.toLowerCase()
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '');
	if (t.startsWith('identit')) return '🪪';
	if (t.startsWith('mission')) return '🎯';
	if (t.startsWith('methode')) return '🛠️';
	if (t.startsWith('livrable')) return '📦';
	if (t.startsWith('garde')) return '🛡️';
	return '•';
};

// Découpe une mission en sections sur les titres markdown (# … à ###### …),
// quel que soit le niveau (# des templates comme ## de l'Atelier). Le texte avant
// le premier titre (préambule) est ignoré : le nom + la description l'affichent déjà.
// Repli : si aucun titre n'est présent, on rend tout le texte en un seul bloc.
export const parseSoulSections = (soul?: string | null): MissionSection[] => {
	if (!soul) return [];
	const chunks = soul.split(/^#{1,6}\s+/m);
	const sections = chunks
		.slice(1)
		.map((p) => p.trim())
		.filter(Boolean)
		.map((p) => {
			const nl = p.indexOf('\n');
			const title = (nl >= 0 ? p.slice(0, nl) : p).trim();
			const body = (nl >= 0 ? p.slice(nl + 1) : '').trim();
			return { title, body, icon: sectionIcon(title) };
		});
	if (sections.length === 0) {
		const whole = soul.trim();
		return whole ? [{ title: 'Mission', body: whole, icon: sectionIcon('mission') }] : [];
	}
	return sections;
};
