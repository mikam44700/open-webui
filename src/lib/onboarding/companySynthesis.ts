// Synthèse du contexte entreprise (onboarding, spec 019) — logique PURE, testable (Vitest).
//
// Le crawl du site (bridge → Crawl4AI) renvoie du markdown ; le MODÈLE ACTIF le résume en
// quatre champs structurés (offre / ton / clientèle / services). Ce module ne fait PAS l'appel
// réseau : il construit le prompt, PARSE la réponse du modèle en un CompanyContext normalisé, et
// le met en forme pour la persistance (USER.md). Règle d'or : jamais inventer — un champ absent,
// illisible ou marqué « non trouvé » reste VIDE (D27, honnêteté d'état).

export type CompanyContext = {
	offre: string;
	tonDeMarque: string;
	clienteleCible: string;
	services: string[];
};

export const EMPTY_CONTEXT: CompanyContext = {
	offre: '',
	tonDeMarque: '',
	clienteleCible: '',
	services: []
};

// Taille max du markdown envoyé au modèle (un site tient largement ; borne le coût / la latence).
const MAX_MARKDOWN_CHARS = 12_000;

// Consigne système : structurer sans jamais inventer, en français.
export const SYNTHESIS_SYSTEM_PROMPT =
	'Tu analyses le contenu du site web d’une entreprise pour en extraire une fiche de contexte. ' +
	'Réponds UNIQUEMENT par un objet JSON valide, sans texte autour, avec exactement ces clés : ' +
	'"offre" (ce que vend l’entreprise, une phrase), "tonDeMarque" (registre/voix, ex. « chaleureux, direct »), ' +
	'"clienteleCible" (à qui elle s’adresse), "services" (tableau des prestations). ' +
	'Reste strictement fidèle au contenu : n’invente RIEN. Si une information est absente, mets une chaîne vide ' +
	'"" (ou un tableau vide pour services) — ne devine jamais. Écris en français.';

// Message utilisateur : le markdown du site, borné en taille.
export const buildSynthesisUserContent = (markdown: string): string => {
	const md = (markdown ?? '').slice(0, MAX_MARKDOWN_CHARS);
	return `Contenu du site :\n\n${md}`;
};

// Valeurs que le modèle peut renvoyer pour dire « je n'ai pas trouvé » — neutralisées en vide.
const PLACEHOLDERS = new Set([
	'',
	'-',
	'—',
	'?',
	'n/a',
	'na',
	'null',
	'none',
	'inconnu',
	'inconnue',
	'aucun',
	'aucune',
	'non trouvé',
	'non trouve',
	'non renseigné',
	'non renseigne',
	'non spécifié',
	'non specifie',
	'non disponible'
]);

const isPlaceholder = (s: string): boolean => PLACEHOLDERS.has(s.trim().toLowerCase());

// Normalise une valeur scalaire en chaîne propre (vide si non-string ou placeholder).
const normStr = (v: unknown): string => {
	if (typeof v !== 'string') return '';
	const s = v.trim();
	return isPlaceholder(s) ? '' : s;
};

// Normalise la liste de services : chaînes propres, sans placeholder, dédupliquées (ordre préservé).
const normServices = (v: unknown): string[] => {
	if (!Array.isArray(v)) return [];
	const seen = new Set<string>();
	const out: string[] = [];
	for (const item of v) {
		const s = normStr(item);
		if (!s) continue;
		const key = s.toLowerCase();
		if (seen.has(key)) continue;
		seen.add(key);
		out.push(s);
	}
	return out;
};

// Extrait l'objet JSON d'une réponse de modèle, tolérant aux fences ```json``` et au texte autour.
const extractJsonObject = (raw: string): unknown => {
	const text = (raw ?? '').trim();
	if (!text) return null;
	// 1) Retire une éventuelle clôture ```json ... ```
	const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
	const candidate = fenced ? fenced[1].trim() : text;
	// 2) Tente un parse direct, sinon isole du premier « { » au dernier « } ».
	for (const src of [candidate, sliceBraces(candidate)]) {
		if (!src) continue;
		try {
			return JSON.parse(src);
		} catch {
			// on tente la variante suivante
		}
	}
	return null;
};

const sliceBraces = (s: string): string | null => {
	const start = s.indexOf('{');
	const end = s.lastIndexOf('}');
	return start >= 0 && end > start ? s.slice(start, end + 1) : null;
};

// Parse la réponse du modèle en CompanyContext normalisé. Ne lève jamais : réponse illisible → vide.
export const parseSynthesis = (raw: string): CompanyContext => {
	const data = extractJsonObject(raw);
	if (!data || typeof data !== 'object') return { ...EMPTY_CONTEXT };
	const obj = data as Record<string, unknown>;
	return {
		offre: normStr(obj.offre),
		tonDeMarque: normStr(obj.tonDeMarque),
		clienteleCible: normStr(obj.clienteleCible),
		services: normServices(obj.services)
	};
};

// Un contexte est-il vide (rien d'exploitable) ? — pour un état honnête (échec de synthèse).
export const isContextEmpty = (c: CompanyContext): boolean =>
	!c.offre.trim() && !c.tonDeMarque.trim() && !c.clienteleCible.trim() && c.services.length === 0;

// Met en forme le contexte validé en texte lisible pour USER.md. Omet les champs vides (aucune
// ligne fantôme) ; contexte vide → chaîne vide (rien à persister).
export const formatContextForProfile = (c: CompanyContext): string => {
	if (isContextEmpty(c)) return '';
	const lines: string[] = ['## Mon entreprise', ''];
	if (c.offre.trim()) lines.push(`- Offre : ${c.offre.trim()}`);
	if (c.clienteleCible.trim()) lines.push(`- Clientèle cible : ${c.clienteleCible.trim()}`);
	if (c.tonDeMarque.trim()) lines.push(`- Ton de marque : ${c.tonDeMarque.trim()}`);
	if (c.services.length) lines.push(`- Services : ${c.services.join(', ')}`);
	return lines.join('\n');
};
