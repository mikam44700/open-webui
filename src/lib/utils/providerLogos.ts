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
	'gemini-color', // Google AI Studio — carré noir (étincelle)
	'nous-research', // Nous Portal — carré noir « NOUS RESEARCH »
	'groq-color' // Groq — carré orange plein (mot-symbole blanc)
]);
