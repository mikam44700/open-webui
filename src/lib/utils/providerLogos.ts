// Logos « carré plein » : le fond fait partie de l'image (couleur ou dégradé), donc on
// les affiche BORD À BORD (object-cover) pour remplir tout le carré, sans deviner de
// couleur. Les logos absents d'ici sont des icônes sur fond blanc/transparent : ils
// gardent le fond blanc + une petite marge (object-contain).
//
// La clé est le nom de fichier du logo (champ `provider.logo` renvoyé par le bridge,
// cf. _LOGO_BY_SLUG dans providers_bridge/hermes_adapter.py).
export const PROVIDER_LOGO_FULL_BLEED = new Set<string>([
	'mimo', // Xiaomi — carré orange
	'nvidia-color', // NVIDIA — carré vert
	'zai', // Zai — carré noir
	'gmi', // GMI Cloud — carré dégradé bleu
	'lmstudio', // LM Studio — carré violet
	'moonshot', // Kimi / Moonshot — carré noir
	'nous-research', // Nous Portal — carré noir « NOUS RESEARCH »
	'groq-color', // Groq — carré orange plein (mot-symbole blanc)
	'perplexity-color' // Perplexity Sonar — carré teal plein
]);

// --- Résolution du logo d'un provider (source UNIQUE, partagée par la page Modèles IA
// et le sélecteur de modèle du chat) -------------------------------------------------

type ProviderLike = { id: string; logo?: string };

// La plupart des logos sont en PNG ; seuls ces quelques-uns restent en SVG.
const SVG_LOGOS = new Set<string>(['api']);

// Nom de fichier du logo. Nous Portal est forcé côté front (« NOUS RESEARCH ») sans
// dépendre du rechargement du bridge ; les autres gardent le logo renvoyé par le bridge.
export const providerLogoFile = (provider: ProviderLike): string =>
	provider.id === 'nous' ? 'nous-research' : provider.logo || 'api';

// URL complète du logo d'un provider.
export const providerLogoUrl = (provider: ProviderLike): string => {
	const file = providerLogoFile(provider);
	const ext = SVG_LOGOS.has(file) ? 'svg' : 'png';
	// URL relative : en dev les logos sont servis par le front (static/), en prod par
	// le backend (build/) — même origine que la page dans les deux cas.
	return `/assets/providers/${file}.${ext}`;
};

// Icône générique de repli si le logo est absent (à brancher sur <img on:error>).
export const PROVIDER_LOGO_FALLBACK = `/assets/providers/api.svg`;

// Logo « carré plein » (fond intégré) → à afficher bord à bord (object-cover).
export const isProviderLogoFullBleed = (provider: ProviderLike): boolean =>
	PROVIDER_LOGO_FULL_BLEED.has(providerLogoFile(provider));
