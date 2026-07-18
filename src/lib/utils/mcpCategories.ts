// Catégories du catalogue MCP (partagées par la page et la modale « Tout parcourir »).
// `expert: true` = catégorie technique, affichée seulement en « Réglages avancés ».
// L'ordre du tableau = ordre d'affichage.

export type McpCategory = { key: string; label: string; emoji: string; expert: boolean };

export const MCP_CATEGORIES: McpCategory[] = [
	{ key: 'productivity', label: 'Productivité & Bureau', emoji: '💼', expert: false },
	{ key: 'finance', label: 'Finance', emoji: '💳', expert: false },
	{ key: 'creation', label: 'Création & Média', emoji: '🎨', expert: false },
	{ key: 'search', label: 'Recherche', emoji: '🔎', expert: false },
	{ key: 'devops', label: 'DevOps & Développement', emoji: '🛠️', expert: true },
	{ key: 'database', label: 'Bases de données', emoji: '🗄️', expert: true },
	{ key: 'crypto', label: 'Crypto & Blockchain', emoji: '⛓️', expert: true },
	{ key: 'tools', label: 'Outils techniques', emoji: '🔧', expert: true },
	{ key: 'other', label: 'Autres', emoji: '📦', expert: true }
];
