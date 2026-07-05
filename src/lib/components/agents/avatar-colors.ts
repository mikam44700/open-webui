// Couleur de bloc par agent — COMBINAISONS de 2 couleurs (palette nommée fournie par l'utilisateur).
// Source unique de vérité (synchro avec tmp/gen_color_preview.py, validé en aperçu).
//
//   - Chaque avatar garde SA couleur dominante (en haut) qui plonge vers un PARTENAIRE harmonieux
//     (en bas) — façon combinaisons Adobe. 1 mix de 2 couleurs par agent, stable, distinct.
//   - Rendu premium : reflet clair de la primaire -> partenaire profond (matière).
//   - Rose / Saumon = FEMMES uniquement (aucun partenaire rose chez les hommes).
//   - Couleurs claires -> `light: true` : la carte passe le texte en foncé (contraste garanti).

import { AVATARS, avatarId, type Gender } from './avatars';

type Entry = { name: string; hex: string; light: boolean; fem: boolean };

// Couleur dominante par avatar (dans l'ordre de la palette). (nom, hex, clair?, féminin?)
const PALETTE: Entry[] = [
	{ name: 'Noir', hex: '#1f2430', light: false, fem: false },
	{ name: 'Gris', hex: '#5b6472', light: false, fem: false },
	{ name: 'Rouge', hex: '#d92222', light: false, fem: false },
	{ name: 'Bleu', hex: '#2563eb', light: false, fem: false },
	{ name: 'Orange', hex: '#ea580c', light: false, fem: false },
	{ name: 'Blanc', hex: '#eef1f6', light: true, fem: false },
	{ name: 'Marron', hex: '#6f4320', light: false, fem: false },
	{ name: 'Jaune', hex: '#f2c015', light: true, fem: false },
	{ name: 'Vert', hex: '#1f9d4d', light: false, fem: false },
	{ name: 'Violet', hex: '#7c3aed', light: false, fem: false },
	{ name: 'Bordeaux', hex: '#8a1533', light: false, fem: false },
	{ name: 'Turquoise', hex: '#12b3a6', light: false, fem: false },
	{ name: 'Cyan', hex: '#06b6d4', light: false, fem: false },
	{ name: 'Bleu marine', hex: '#1e3a8a', light: false, fem: false },
	{ name: 'Or', hex: '#d0a01a', light: true, fem: false },
	{ name: 'Tomate', hex: '#ef533b', light: false, fem: false },
	{ name: 'Sarcelle', hex: '#0f766e', light: false, fem: false },
	{ name: 'Citron vert', hex: '#84cc16', light: true, fem: false },
	{ name: 'Blé', hex: '#d9c29a', light: true, fem: false },
	{ name: 'Olive', hex: '#6b7a0f', light: false, fem: false },
	{ name: 'Aqua', hex: '#22d3ee', light: true, fem: false },
	{ name: 'Chocolat', hex: '#5c3a21', light: false, fem: false },
	{ name: 'Azur', hex: '#0ea5e9', light: false, fem: false },
	{ name: 'Argent', hex: '#a9b3c1', light: true, fem: false },
	{ name: 'Bronze', hex: '#9c6b3f', light: false, fem: false },
	{ name: 'Bleu foncé', hex: '#1e40af', light: false, fem: false },
	{ name: 'Marine', hex: '#182449', light: false, fem: false },
	{ name: 'Rose', hex: '#ec4899', light: false, fem: true },
	{ name: 'Saumon', hex: '#fa8072', light: true, fem: true }
];
const PAL_MEN = PALETTE.filter((p) => !p.fem); // pas de rose/saumon chez les hommes

// Partenaire harmonieux par couleur (combinaisons validées). Aucun partenaire rose côté hommes.
const COMBO: Record<string, string> = {
	Noir: '#1e3a8a', Gris: '#2563eb', Rouge: '#d0a01a', Bleu: '#7c3aed', Orange: '#1e3a8a',
	Blanc: '#a9b3c1', Marron: '#d0a01a', Jaune: '#ea580c', Vert: '#12b3a6', Violet: '#2563eb',
	Bordeaux: '#7c3aed', Turquoise: '#2563eb', Cyan: '#2563eb', 'Bleu marine': '#06b6d4',
	Or: '#ea580c', Tomate: '#d0a01a', Sarcelle: '#84cc16', 'Citron vert': '#1f9d4d', 'Blé': '#12b3a6',
	Olive: '#1f9d4d', Aqua: '#2563eb', Chocolat: '#d0a01a', Azur: '#7c3aed', Argent: '#2563eb',
	Bronze: '#0f766e', 'Bleu foncé': '#7c3aed', Marine: '#06b6d4', Rose: '#7c3aed', Saumon: '#ec4899'
};

// --- helpers couleur (HSL) -----------------------------------------------------
const hexToRgb = (h: string): [number, number, number] => [
	parseInt(h.slice(1, 3), 16),
	parseInt(h.slice(3, 5), 16),
	parseInt(h.slice(5, 7), 16)
];
const rgbToHex = (r: number, g: number, b: number): string =>
	'#' + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('');

const rgbToHsl = (r: number, g: number, b: number): [number, number, number] => {
	r /= 255; g /= 255; b /= 255;
	const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
	let h = 0, s = 0;
	if (d !== 0) {
		s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
		if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
		else if (max === g) h = (b - r) / d + 2;
		else h = (r - g) / d + 4;
		h /= 6;
	}
	return [h, s, l];
};
const hslToRgb = (h: number, s: number, l: number): [number, number, number] => {
	if (s === 0) return [l * 255, l * 255, l * 255];
	const hue2rgb = (p: number, q: number, t: number) => {
		if (t < 0) t += 1;
		if (t > 1) t -= 1;
		if (t < 1 / 6) return p + (q - p) * 6 * t;
		if (t < 1 / 2) return q;
		if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
		return p;
	};
	const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
	return [hue2rgb(p, q, h + 1 / 3) * 255, hue2rgb(p, q, h) * 255, hue2rgb(p, q, h - 1 / 3) * 255];
};

// Combinaison : primaire (reflet clair, haut) -> partenaire (profond, bas).
const gradCombo = (prim: string, part: string): string => {
	const [ph, ps, pl] = rgbToHsl(...hexToRgb(prim));
	const [qh, qs, ql] = rgbToHsl(...hexToRgb(part));
	const top = rgbToHex(...hslToRgb(ph, ps * 0.92, Math.min(pl + 0.08, 0.93)));
	const bot = rgbToHex(...hslToRgb(qh, Math.min(qs * 1.05, 1), Math.max(ql - 0.1, 0.12)));
	return `linear-gradient(140deg, ${top}, ${bot})`;
};

export type BlockColor = { gradient: string; light: boolean };

// Table figée id -> combinaison (index dans le groupe de genre, comme l'aperçu).
const TABLE: Record<string, BlockColor> = (() => {
	const map: Record<string, BlockColor> = {};
	const build = (gender: Gender, pal: Entry[]) => {
		AVATARS.filter((a) => a.gender === gender).forEach((a, k) => {
			const p = pal[k % pal.length];
			map[a.id] = { gradient: gradCombo(p.hex, COMBO[p.name] ?? p.hex), light: p.light };
		});
	};
	build('female', PALETTE);
	build('male', PAL_MEN);
	return map;
})();

// Surcharges signature (échange Adam/Enzo + Mike indigo), fonds sombres -> texte blanc.
const OVERRIDES: Record<string, BlockColor> = {
	adam: { gradient: gradCombo('#7c3aed', '#2563eb'), light: false }, // Violet + Bleu
	enzo: { gradient: gradCombo('#1f2430', '#1e3a8a'), light: false }, // Noir + Marine
	mike: { gradient: gradCombo('#4338ca', '#7c3aed'), light: false } // Indigo + Violet (bandeau)
};

// Repli stable (id inconnu / agent sans avatar) : une couleur homme, dérivée du nom.
const fallback = (seed: string): BlockColor => {
	let h = 0;
	for (let i = 0; i < (seed?.length ?? 0); i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
	const p = PAL_MEN[h % PAL_MEN.length];
	return { gradient: gradCombo(p.hex, COMBO[p.name] ?? p.hex), light: p.light };
};

/** Couleur de bloc (dégradé combiné + `light` pour le contraste) d'un agent, par id d'avatar ou nom. */
export const avatarColor = (key: string | null | undefined): BlockColor => {
	if (!key) return fallback('agent');
	const id = TABLE[key] ? key : avatarId(key);
	return OVERRIDES[id] ?? TABLE[id] ?? fallback(key);
};

/** Compat : dégradé seul. */
export const avatarGradient = (key: string | null | undefined): string => avatarColor(key).gradient;
