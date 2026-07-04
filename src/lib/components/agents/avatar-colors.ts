// Couleur de bloc par agent — FLASHY, stable, gender-aware. Source unique de vérité.
//
// Principe (validé en aperçu, cf. scripts scratchpad/gen_color_preview.py) :
//   - Chaque avatar du catalogue figé (AVATARS) reçoit UN dégradé, calculé une fois, figé par id.
//   - Teintes réparties par angle d'or (bien distinctes) sur 2 niveaux de luminosité (vif clair /
//     vif profond) pour multiplier les couleurs perçues sans perdre le punch.
//   - OKLCH : intensité perçue homogène (rendu premium) ; chroma poussé = couleur qui claque.
//   - Genre : hommes JAMAIS de rose/magenta (teintes 0–320) ; femmes toutes teintes, jamais sombres.
// La couleur suit l'AGENT (via son avatar), donc elle est identique partout (catalogue + « Mes
// agents ») et ne change jamais quand la liste bouge.

import { AVATARS, avatarId, type Gender } from './avatars';

const GOLDEN = 137.508;

// Familles (chroma, luminosité de base). 2 niveaux vifs.
const FAM_FEMALE: [number, number][] = [
	[0.2, 0.62], // vif clair
	[0.19, 0.545] // vif profond (jamais sombre)
];
const FAM_MALE: [number, number][] = [
	[0.2, 0.6],
	[0.19, 0.515]
];

const grad = (hue: number, c: number, l: number): string => {
	const top = `oklch(${(l + 0.045).toFixed(3)} ${c} ${(hue - 6).toFixed(1)})`;
	const bot = `oklch(${(l - 0.045).toFixed(3)} ${c} ${(hue + 6).toFixed(1)})`;
	return `linear-gradient(135deg, ${top}, ${bot})`;
};

// Table figée id -> dégradé (même logique que l'aperçu : index dans le groupe de genre).
const TABLE: Record<string, string> = (() => {
	const map: Record<string, string> = {};
	const build = (list: typeof AVATARS, fams: [number, number][], span: number) => {
		list.forEach((a, k) => {
			const hue = (k * GOLDEN) % span;
			const [c, l] = fams[k % fams.length];
			map[a.id] = grad(hue, c, l);
		});
	};
	build(
		AVATARS.filter((a) => a.gender === 'female'),
		FAM_FEMALE,
		360
	);
	build(
		AVATARS.filter((a) => a.gender === 'male'),
		FAM_MALE,
		320
	);
	return map;
})();

// Surcharges manuelles pour les rares clashs vêtements/fond (repérés à l'aperçu). Vide pour l'instant.
const OVERRIDES: Record<string, string> = {};

// Repli stable pour un id absent de la table / un agent sans avatar : dégradé dérivé du nom (sans rose).
const fallback = (seed: string): string => {
	let h = 0;
	for (let i = 0; i < (seed?.length ?? 0); i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
	return grad(h % 320, 0.19, 0.55);
};

/**
 * Dégradé de bloc pour un agent. `key` = identifiant d'avatar (ex. "emma") OU, à défaut, le nom de
 * l'agent (repli neutre stable). Accepte aussi un chemin d'avatar (on en extrait l'id).
 */
export const avatarGradient = (key: string | null | undefined, _gender?: Gender): string => {
	if (!key) return fallback('agent');
	const id = TABLE[key] ? key : avatarId(key); // accepte id brut ou chemin "/assets/agents/emma.png"
	return OVERRIDES[id] ?? TABLE[id] ?? fallback(key);
};
