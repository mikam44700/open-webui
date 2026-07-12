// Synthèse du contexte entreprise (onboarding, spec 019) — logique PURE, testable (Vitest).
//
// Le crawl MULTI-PAGES du site (bridge → Crawl4AI : home + pages clés) renvoie du markdown ; le
// MODÈLE ACTIF le résume en une fiche structurée (10 blocs). Ce module ne fait PAS l'appel réseau :
// il construit le prompt, PARSE la réponse du modèle en un CompanyContext normalisé, et le met en
// forme pour la persistance (USER.md).
//
// Règle d'or (D27) : jamais inventer une donnée FACTUELLE (nom, chiffres, coordonnées) absente du
// site. En revanche, pour la clientèle et les problèmes résolus, le modèle a le droit de RELIER et
// REFORMULER ce qui est clairement impliqué par l'offre, le secteur et les témoignages (ex. un
// logiciel « pour restaurants » → clientèle = restaurateurs ; « je dors mieux la nuit » → il
// résout le stress de gestion). Un champ sans aucun appui dans le texte reste VIDE. Les concurrents
// ne sont volontairement PAS extraits (une entreprise ne les liste pas sur son site → V2 sourcé).

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
	'de contexte FACTUELLE, exploitable par un assistant. Réponds UNIQUEMENT par un objet JSON valide, ' +
	'sans texte autour, avec EXACTEMENT ces clés :\n' +
	'- "nomEntreprise" : le nom de l’entreprise\n' +
	'- "secteur" : son secteur d’activité / métier\n' +
	'- "coordonnees" : téléphone, email, adresse, horaires, zone géographique. Utilise ce qui est ' +
	'indiqué, ET en particulier le bloc « Coordonnées repérées sur le site » s’il est présent plus bas ' +
	'(téléphone/email/adresse extraits du pied de page) — recopie ces valeurs telles quelles\n' +
	'- "offre" : ce qu’elle vend, en une phrase claire\n' +
	'- "services" : tableau des prestations/produits proposés\n' +
	'- "tonDeMarque" : le registre/voix, DÉRIVÉ du style réel des textes du site (ex. « chaleureux, ' +
	'direct ») — jamais un adjectif marketing deviné\n' +
	'- "vocabulaire" : tableau des mots/expressions/noms d’offres propres à l’entreprise, récurrents\n' +
	'- "clienteleCible" : à qui l’entreprise s’adresse. Appuie-toi sur ce qui est écrit MAIS aussi sur ' +
	'ce qui est clairement impliqué par l’offre, le secteur et les témoignages (ex. un logiciel de ' +
	'caisse « pour restaurants » → clientèle = restaurateurs et gérants d’établissements). Reste ' +
	'concret ; n’invente pas un persona sans aucun appui dans le texte\n' +
	'- "problemesResolus" : les difficultés, besoins ou frustrations des clients que l’entreprise ' +
	'résout. Déduis-les des bénéfices mis en avant, des pages « pourquoi nous / besoins / ' +
	'fonctionnalités » ET des témoignages (ex. « je dors mieux la nuit » ou « avant on recopiait ' +
	'toutes les commandes » → problèmes = charge mentale, ressaisie manuelle, dispersion des outils). ' +
	'Reformule fidèlement en une ou deux phrases ; n’en fabrique pas un sans aucun appui\n' +
	'- "preuveSociale" : tableau — clients références, chiffres clés, certifications, avis/témoignages ' +
	'CITÉS sur le site\n\n' +
	'RÈGLE : reste fidèle au site. N’invente aucune donnée FACTUELLE (nom, chiffres, coordonnées, ' +
	'certifications) qui n’y figure pas. Pour la clientèle et les problèmes résolus, tu PEUX relier et ' +
	'reformuler ce qui est clairement impliqué par l’offre et les témoignages, sans jamais fabriquer un ' +
	'élément sans appui. Un champ sans aucun appui dans le texte → chaîne vide "" (ou tableau vide). ' +
	'Écris en français.';

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

// Limite de USER.md : le moteur Hermes injecte ce fichier dans le prompt de CHAQUE agent, et son
// `memory_tool` le borne (défaut `user_char_limit` = 1375 ≈ 500 tokens). USER.md doit donc rester
// CONCIS : l'essentiel qui personnalise les agents. Le détail complet (tous les services, les
// témoignages verbatim) part au COFFRE (cherchable) via `formatContextForKnowledge`. On vise une
// marge sous 1375 pour laisser de la place au profil du dirigeant (interview) qui rejoint USER.md.
export const USER_PROFILE_MAX_CHARS = 1350;

// Plafonne un texte de profil à `max` caractères en ne gardant que des LIGNES entières (jamais de
// coupe en milieu de phrase) : l'en-tête + autant de lignes prioritaires (dans l'ordre) que possible.
export const capProfileText = (text: string, max: number = USER_PROFILE_MAX_CHARS): string => {
	if (text.length <= max) return text;
	const out: string[] = [];
	let len = 0;
	for (const line of text.split('\n')) {
		if (len + line.length + 1 > max) {
			if (out.length <= 2) continue; // garde au moins l'en-tête, sinon saute juste la ligne trop longue
			continue;
		}
		out.push(line);
		len += line.length + 1;
	}
	return out.join('\n').trimEnd();
};

// Preuves courtes uniquement (chiffres, notes, certifs) : les témoignages verbatim (longs) sont du
// bruit dans un prompt d'agent → ils restent dans la fiche complète (coffre), pas dans USER.md.
const SHORT_PROOF_MAX = 140;

// Écrête une valeur à `n` caractères sans couper un mot (ajoute « … »). Garde USER.md lisible et lean.
const clip = (s: string, n: number): string => {
	const t = s.trim();
	if (t.length <= n) return t;
	return t.slice(0, n).replace(/\s+\S*$/, '') + '…';
};

// Fiche CONCISE pour USER.md : essentiel personnalisant, champs écrêtés, listes bornées, preuves
// courtes. Ordre = priorité (le plus utile aux agents d'abord) — `capProfileText` peut retirer la
// queue (vocabulaire…) pour tenir dans la limite ; le coffre garde tout. Contexte vide → ''.
export const formatContextForProfile = (c: CompanyContext): string => {
	if (isContextEmpty(c)) return '';
	const lines: string[] = ['## Mon entreprise', ''];
	if (c.nomEntreprise.trim()) lines.push(`- Nom : ${clip(c.nomEntreprise, 80)}`);
	if (c.secteur.trim()) lines.push(`- Secteur : ${clip(c.secteur, 90)}`);
	if (c.offre.trim()) lines.push(`- Offre : ${clip(c.offre, 180)}`);
	if (c.clienteleCible.trim()) lines.push(`- Clientèle cible : ${clip(c.clienteleCible, 120)}`);
	if (c.coordonnees.trim()) lines.push(`- Coordonnées : ${clip(c.coordonnees, 200)}`);
	if (c.tonDeMarque.trim()) lines.push(`- Ton de marque : ${clip(c.tonDeMarque, 120)}`);
	if (c.problemesResolus.trim()) lines.push(`- Problèmes résolus : ${clip(c.problemesResolus, 200)}`);
	if (c.services.length) lines.push(`- Services : ${clip(c.services.slice(0, 8).join(', '), 300)}`);
	const shortProofs = c.preuveSociale.filter((p) => p.length <= SHORT_PROOF_MAX).slice(0, 4);
	if (shortProofs.length) lines.push(`- Preuves / réassurance : ${clip(shortProofs.join(', '), 180)}`);
	if (c.vocabulaire.length) lines.push(`- Vocabulaire maison : ${clip(c.vocabulaire.slice(0, 10).join(', '), 140)}`);
	return lines.join('\n');
};

// Fiche COMPLÈTE pour le COFFRE (note datée, cherchable) : tout, sans borne — y compris tous les
// services et les témoignages verbatim. C'est la mémoire riche, pas le prompt injecté.
export const formatContextForKnowledge = (c: CompanyContext): string => {
	if (isContextEmpty(c)) return '';
	const lines: string[] = ['## Mon entreprise', ''];
	if (c.nomEntreprise.trim()) lines.push(`- Nom : ${c.nomEntreprise.trim()}`);
	if (c.secteur.trim()) lines.push(`- Secteur : ${c.secteur.trim()}`);
	if (c.offre.trim()) lines.push(`- Offre : ${c.offre.trim()}`);
	if (c.clienteleCible.trim()) lines.push(`- Clientèle cible : ${c.clienteleCible.trim()}`);
	if (c.services.length) lines.push(`- Services : ${c.services.join(', ')}`);
	if (c.tonDeMarque.trim()) lines.push(`- Ton de marque : ${c.tonDeMarque.trim()}`);
	if (c.problemesResolus.trim()) lines.push(`- Problèmes résolus : ${c.problemesResolus.trim()}`);
	if (c.preuveSociale.length) lines.push(`- Preuves / réassurance : ${c.preuveSociale.join(' · ')}`);
	if (c.vocabulaire.length) lines.push(`- Vocabulaire maison : ${c.vocabulaire.join(', ')}`);
	if (c.coordonnees.trim()) lines.push(`- Coordonnées : ${c.coordonnees.trim()}`);
	return lines.join('\n');
};
