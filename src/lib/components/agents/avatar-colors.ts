// Couleur de bloc par agent — 24 COULEURS FRANCHES Tailwind (confort/premium), dégradé 3 tons.
// Source unique de vérité (synchro avec tmp/gen_24.py, validé en aperçu).
//
//   - 24 vraies teintes distinctes (une par famille, pas des variantes qui se ressemblent),
//     réparties sur les 100 agents en ordre dispersé (jamais deux mêmes côte à côte).
//   - Rendu CONFORT (anti-fatigue) : saturation adoucie, tons profonds, voyage de couleur doux.
//   - Dégradé diagonal 135° à 3 tons (foncé sous le nom -> voisin -> moyen-profond) = effet premium.
//   - Rose (Fuchsia/Rose/Framboise) = FEMMES uniquement. Texte blanc (light:false).
//   - SIGNATURE : Mike (orchestrateur) a une couleur RÉSERVÉE hors des 24 (Or doré) = unique dans l'app.

import { AVATARS, avatarId, type Gender } from './avatars';

type Color = { name: string; hex: string; fem: boolean };

// 24 teintes franches (ordre volontairement dispersé pour contraster les voisins). Rose -> femmes.
const COLORS: Color[] = [
	{ name: 'Rouge', hex: '#dc2626', fem: false },
	{ name: 'Émeraude', hex: '#059669', fem: false },
	{ name: 'Bleu', hex: '#2563eb', fem: false },
	{ name: 'Ambre', hex: '#d97706', fem: false },
	{ name: 'Violet', hex: '#7c3aed', fem: false },
	{ name: 'Cyan', hex: '#0891b2', fem: false },
	{ name: 'Fuchsia', hex: '#c026d3', fem: true },
	{ name: 'Vert', hex: '#16a34a', fem: false },
	{ name: 'Indigo', hex: '#4f46e5', fem: false },
	{ name: 'Orange', hex: '#ea580c', fem: false },
	{ name: 'Turquoise', hex: '#0d9488', fem: false },
	{ name: 'Rose', hex: '#db2777', fem: true },
	{ name: 'Mauve', hex: '#9333ea', fem: false },
	{ name: 'Bleu ciel', hex: '#0284c7', fem: false },
	{ name: 'Jaune', hex: '#ca8a04', fem: false },
	{ name: 'Marine', hex: '#1e3a8a', fem: false },
	{ name: 'Framboise', hex: '#e11d48', fem: true },
	{ name: 'Lime', hex: '#65a30d', fem: false },
	{ name: 'Aubergine', hex: '#581c87', fem: false },
	{ name: 'Sapin', hex: '#14532d', fem: false },
	{ name: 'Ardoise', hex: '#475569', fem: false },
	{ name: 'Bordeaux', hex: '#7f1d1d', fem: false },
	{ name: 'Marron', hex: '#78350f', fem: false },
	{ name: 'Anthracite', hex: '#1e293b', fem: false }
];

// --- helpers couleur -----------------------------------------------------------
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

const relLum = (r: number, g: number, b: number): number => {
	const f = (c: number) => {
		c /= 255;
		return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
	};
	return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const whiteRatio = (rgb: [number, number, number]): number => 1.05 / (relLum(...rgb) + 0.05);

// Dégradé CONFORT 3 tons : foncé (nom) -> voisin -> moyen-profond. Saturation adoucie, tons profonds.
const blockGradient = (base: string): string => {
	const [h, s, l] = rgbToHsl(...hexToRgb(base));
	const neutral = s < 0.12;
	const sf = neutral ? s : Math.min(s * 0.9, 0.64); // saturation adoucie (anti-fatigue)
	const shift = neutral ? 0 : 0.05;
	const botlift = 0.2;

	// Haut-gauche (nom) : assombri juste assez pour le blanc.
	let tl = Math.min(l, 0.42);
	let top = hslToRgb(h, sf, tl);
	let guard = 0;
	while (whiteRatio(top) < 3.3 && tl > 0.08 && guard++ < 60) {
		tl -= 0.02;
		top = hslToRgb(h, sf, tl);
	}
	const TOP = rgbToHex(...top);
	const MID = rgbToHex(...hslToRgb((h + shift) % 1, sf, Math.min(Math.max(l, 0.42) + botlift * 0.5, 0.46)));
	const BOT = rgbToHex(...hslToRgb((h + shift * 1.5) % 1, sf, Math.min(Math.max(l, 0.4) + botlift, 0.52)));
	return `linear-gradient(135deg, ${TOP} 0%, ${MID} 50%, ${BOT} 100%)`;
};

// Un dégradé figé par couleur (les mêmes couleurs = même rendu, assumé).
const GRAD: Record<string, string> = Object.fromEntries(COLORS.map((c) => [c.name, blockGradient(c.hex)]));

// Couleurs SIGNATURE (hors des 24 en rotation) : réservées à un agent précis, uniques dans toute l'app.
// Mike = l'orchestrateur -> Or doré premium (leadership, chef d'orchestre). Texte blanc.
const SIGNATURE: Record<string, { hex: string; label: string }> = {
	mike: { hex: '#b45309', label: 'Or (Mike, orchestrateur)' }
};
const SIG_GRAD: Record<string, string> = Object.fromEntries(
	Object.entries(SIGNATURE).map(([id, s]) => [id, blockGradient(s.hex)])
);

const NONFEM = COLORS.filter((c) => !c.fem); // 21 (sans rose) -> hommes

export type BlockColor = { gradient: string; light: boolean; colorName: string };

// Couleur par agent : femmes cyclent les 24, hommes les 21 non-roses (ordre du fichier).
const nameOf: Record<string, string> = {};
const assign = (gender: Gender, pool: Color[]) => {
	AVATARS.filter((a) => a.gender === gender).forEach((a, k) => {
		nameOf[a.id] = pool[k % pool.length].name;
	});
};
assign('female', COLORS);
assign('male', NONFEM);

// Échanges de couleur demandés (avatar/nom inchangés).
const swap = (a: string, b: string) => {
	if (nameOf[a] && nameOf[b]) {
		const t = nameOf[a];
		nameOf[a] = nameOf[b];
		nameOf[b] = t;
	}
};
swap('adam', 'bastien');
swap('antoine', 'adam');
swap('enzo', 'erik');

// Repli stable (id inconnu / agent sans avatar) : une couleur homme dérivée du nom.
const fallbackName = (seed: string): string => {
	let h = 0;
	for (let i = 0; i < (seed?.length ?? 0); i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
	return NONFEM[h % NONFEM.length].name;
};

/** Couleur de bloc (dégradé + `light` pour le contraste) d'un agent, par id d'avatar ou nom. */
export const avatarColor = (key: string | null | undefined): BlockColor => {
	const id = key && (nameOf[key] || SIGNATURE[key]) ? key : avatarId(key ?? '');
	const sig = SIGNATURE[id];
	if (sig) return { gradient: SIG_GRAD[id], light: false, colorName: sig.label };
	const name = nameOf[id] ?? fallbackName(key ?? 'agent');
	return { gradient: GRAD[name], light: false, colorName: name };
};

/** Compat : dégradé seul. */
export const avatarGradient = (key: string | null | undefined): string => avatarColor(key).gradient;
