// Synthèse du contexte entreprise (onboarding, spec 019) — logique PURE, testable (Vitest).
//
// Le crawl MULTI-PAGES du site (bridge → Crawl4AI : home + pages clés) renvoie du markdown ; le
// MODÈLE ACTIF le résume en une fiche structurée (10 blocs). Ce module ne fait PAS l'appel réseau :
// il construit le prompt, PARSE la réponse du modèle en un CompanyContext normalisé, et le met en
// forme pour la persistance (USER.md).
//
// Règle d'or (D27) : jamais inventer. Un champ absent, illisible ou marqué « non trouvé » reste
// VIDE. Les champs à fort risque d'hallucination (clientèle, problèmes résolus, ton) sont cadrés
// par une consigne stricte « uniquement ce qui est écrit noir sur blanc ». Les concurrents ne sont
// volontairement PAS extraits (une entreprise ne les liste pas sur son site → chantier V2 sourcé).

export type CompanyContext = {
	// Identité
	nomEntreprise: string;
	secteur: string;
	coordonnees: string;
	// Offre
	offre: string;
	services: string[];
	tonDeMarque: string;
	vocabulaire: string[];
	// Marché
	clienteleCible: string;
	problemesResolus: string;
	preuveSociale: string[];
};

export const EMPTY_CONTEXT: CompanyContext = {
	nomEntreprise: '',
	secteur: '',
	coordonnees: '',
	offre: '',
	services: [],
	tonDeMarque: '',
	vocabulaire: [],
	clienteleCible: '',
	problemesResolus: '',
	preuveSociale: []
};

// Taille max du markdown envoyé au modèle. Relevée pour le crawl MULTI-PAGES (home + pages clés
// fusionnées) : gpt-5-mini a un très grand contexte, ~24k caractères = coût/latence négligeables.
const MAX_MARKDOWN_CHARS = 24_000;

// Consigne système : extraire une fiche factuelle, sans jamais inventer, en français. Les champs
// interprétatifs (clientèle, problèmes, ton) portent une consigne stricte anti-hallucination.
export const SYNTHESIS_SYSTEM_PROMPT =
	'Tu analyses le contenu du site web d’une entreprise (plusieurs pages) pour en extraire une fiche ' +
	'de contexte FACTUELLE. Réponds UNIQUEMENT par un objet JSON valide, sans texte autour, avec ' +
	'EXACTEMENT ces clés :\n' +
	'- "nomEntreprise" : le nom de l’entreprise\n' +
	'- "secteur" : son secteur d’activité / métier\n' +
	'- "coordonnees" : téléphone, email, adresse, horaires, zone géographique — ce qui est indiqué\n' +
	'- "offre" : ce qu’elle vend, en une phrase claire\n' +
	'- "services" : tableau des prestations/produits proposés\n' +
	'- "tonDeMarque" : le registre/voix, DÉRIVÉ du style réel des textes du site (ex. « chaleureux, ' +
	'direct ») — jamais un adjectif marketing deviné\n' +
	'- "vocabulaire" : tableau des mots/expressions/noms d’offres propres à l’entreprise, récurrents\n' +
	'- "clienteleCible" : à qui elle s’adresse — UNIQUEMENT si c’est écrit explicitement ; ne déduis ' +
	'JAMAIS un persona non écrit\n' +
	'- "problemesResolus" : les problèmes, besoins ou difficultés des clients que le site ÉVOQUE et ' +
	'que l’entreprise dit résoudre (regarde en particulier les pages « pourquoi nous », « besoins », ' +
	'« fonctionnalités », « solutions »). Reformule fidèlement ce qui est mentionné ; ne fabrique ' +
	'pas un problème totalement absent du site\n' +
	'- "preuveSociale" : tableau — clients références, chiffres clés, certifications, avis/témoignages ' +
	'CITÉS sur le site\n\n' +
	'RÈGLE ABSOLUE : reste strictement fidèle au contenu. N’invente RIEN, ne déduis RIEN. Si une ' +
	'information est absente du site, mets une chaîne vide "" (ou un tableau vide). Ne devine jamais ' +
	'un persona, un problème ou un ton non écrit. Écris en français.';

// Message utilisateur : le markdown du site (multi-pages), borné en taille.
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

// Normalise une liste : chaînes propres, sans placeholder, dédupliquées (ordre préservé).
const normList = (v: unknown): string[] => {
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
		nomEntreprise: normStr(obj.nomEntreprise),
		secteur: normStr(obj.secteur),
		coordonnees: normStr(obj.coordonnees),
		offre: normStr(obj.offre),
		services: normList(obj.services),
		tonDeMarque: normStr(obj.tonDeMarque),
		vocabulaire: normList(obj.vocabulaire),
		clienteleCible: normStr(obj.clienteleCible),
		problemesResolus: normStr(obj.problemesResolus),
		preuveSociale: normList(obj.preuveSociale)
	};
};

// Un contexte est-il vide (rien d'exploitable) ? — pour un état honnête (échec de synthèse → repli
// manuel). Vide = tous les champs texte vides ET toutes les listes vides.
export const isContextEmpty = (c: CompanyContext): boolean =>
	!c.nomEntreprise.trim() &&
	!c.secteur.trim() &&
	!c.coordonnees.trim() &&
	!c.offre.trim() &&
	!c.tonDeMarque.trim() &&
	!c.clienteleCible.trim() &&
	!c.problemesResolus.trim() &&
	c.services.length === 0 &&
	c.vocabulaire.length === 0 &&
	c.preuveSociale.length === 0;

// Met en forme le contexte validé en texte lisible pour USER.md. Omet les champs vides (aucune
// ligne fantôme) ; contexte vide → chaîne vide (rien à persister).
export const formatContextForProfile = (c: CompanyContext): string => {
	if (isContextEmpty(c)) return '';
	const lines: string[] = ['## Mon entreprise', ''];
	if (c.nomEntreprise.trim()) lines.push(`- Nom : ${c.nomEntreprise.trim()}`);
	if (c.secteur.trim()) lines.push(`- Secteur : ${c.secteur.trim()}`);
	if (c.offre.trim()) lines.push(`- Offre : ${c.offre.trim()}`);
	if (c.clienteleCible.trim()) lines.push(`- Clientèle cible : ${c.clienteleCible.trim()}`);
	if (c.services.length) lines.push(`- Services : ${c.services.join(', ')}`);
	if (c.tonDeMarque.trim()) lines.push(`- Ton de marque : ${c.tonDeMarque.trim()}`);
	if (c.problemesResolus.trim()) lines.push(`- Problèmes résolus : ${c.problemesResolus.trim()}`);
	if (c.preuveSociale.length) lines.push(`- Preuves / réassurance : ${c.preuveSociale.join(', ')}`);
	if (c.vocabulaire.length) lines.push(`- Vocabulaire maison : ${c.vocabulaire.join(', ')}`);
	if (c.coordonnees.trim()) lines.push(`- Coordonnées : ${c.coordonnees.trim()}`);
	return lines.join('\n');
};
