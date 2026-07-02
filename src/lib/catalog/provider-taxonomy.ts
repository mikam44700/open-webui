/**
 * Taxonomie des fournisseurs de « Clés API » (page Modèles IA).
 *
 * Deux axes complémentaires, keyés par identifiant de fournisseur (source : bridge
 * `list_providers`) :
 *  - GROUP  : regroupement principal de la grille (familiarité + fonction), avec
 *             en-têtes de section. Met en avant ce qu'un dirigeant reconnaît.
 *  - REGION : origine / juridiction du fournisseur (souveraineté), affichée en badge
 *             sur chaque carte.
 *
 * Règle d'honnêteté : la région indique l'origine du fournisseur / de l'endpoint,
 * PAS une promesse sur l'hébergement physique des données. Un identifiant inconnu de
 * la table tombe dans le groupe « Autres » (en fin de liste) et n'a aucun badge région.
 *
 * NB : les axes sont indépendants — un fournisseur peut être un « grand nom »
 * mondialement connu ET d'origine chinoise (ex. DeepSeek). Le groupe reflète la
 * notoriété/fonction, le badge région reflète la souveraineté.
 */

export type ProviderGroup = 'grands-noms' | 'passerelle' | 'hebergement' | 'chinois' | 'custom';
export type ProviderRegion = 'us' | 'cn' | 'eu' | 'ca' | 'intl' | 'local';

/** Ordre officiel d'affichage des sections. */
export const GROUP_ORDER: ProviderGroup[] = [
	'grands-noms',
	'passerelle',
	'hebergement',
	'chinois',
	'custom'
];

export const GROUP_LABEL: Record<ProviderGroup, string> = {
	'grands-noms': 'Les grands noms',
	passerelle: 'Une seule clé, plein de modèles',
	hebergement: "Plateformes d'hébergement",
	chinois: 'Modèles chinois',
	custom: 'Sur-mesure'
};

/** Groupe (familiarité + fonction) par identifiant de fournisseur. */
const GROUP_BY_ID: Record<string, ProviderGroup> = {
	// Les grands noms (mondialement reconnus)
	'openai-api': 'grands-noms',
	anthropic: 'grands-noms',
	gemini: 'grands-noms',
	vertex: 'grands-noms',
	xai: 'grands-noms',
	deepseek: 'grands-noms',
	copilot: 'grands-noms',
	mistral: 'grands-noms',
	cohere: 'grands-noms',
	perplexity: 'grands-noms',
	// Une seule clé, plein de modèles (passerelles / agrégateurs)
	openrouter: 'passerelle',
	moa: 'passerelle',
	kilocode: 'passerelle',
	'opencode-zen': 'passerelle',
	'opencode-go': 'passerelle',
	// Plateformes d'hébergement (open source / infra hébergée)
	novita: 'hebergement',
	nvidia: 'hebergement',
	huggingface: 'hebergement',
	'ollama-cloud': 'hebergement',
	arcee: 'hebergement',
	gmi: 'hebergement',
	'azure-foundry': 'hebergement',
	groq: 'hebergement',
	cerebras: 'hebergement',
	together: 'hebergement',
	fireworks: 'hebergement',
	// Modèles chinois (labos / endpoints Chine)
	alibaba: 'chinois',
	'alibaba-coding-plan': 'chinois',
	xiaomi: 'chinois',
	'tencent-tokenhub': 'chinois',
	zai: 'chinois',
	'kimi-coding': 'chinois',
	'kimi-coding-cn': 'chinois',
	stepfun: 'chinois',
	minimax: 'chinois',
	'minimax-cn': 'chinois',
	'baidu-ernie': 'chinois',
	// Sur-mesure
	custom: 'custom'
};

/** Drapeau / pictogramme affiché sur la carte (léger). */
export const REGION_FLAG: Record<ProviderRegion, string> = {
	us: '🇺🇸',
	cn: '🇨🇳',
	eu: '🇪🇺',
	ca: '🇨🇦',
	intl: '🌍',
	local: '💻'
};

/** Nom complet, montré au survol (infobulle) pour rester clair. */
export const REGION_NAME: Record<ProviderRegion, string> = {
	us: 'États-Unis',
	cn: 'Chine',
	eu: 'Europe',
	ca: 'Canada',
	intl: 'International',
	local: 'Local'
};

/** Origine / juridiction par identifiant de fournisseur (souveraineté). */
const REGION_BY_ID: Record<string, ProviderRegion> = {
	// États-Unis
	'openai-api': 'us',
	anthropic: 'us',
	gemini: 'us',
	vertex: 'us',
	xai: 'us',
	copilot: 'us',
	nvidia: 'us',
	arcee: 'us',
	'azure-foundry': 'us',
	'ollama-cloud': 'us',
	// Chine
	deepseek: 'cn',
	alibaba: 'cn',
	'alibaba-coding-plan': 'cn',
	xiaomi: 'cn',
	'tencent-tokenhub': 'cn',
	zai: 'cn',
	'kimi-coding': 'cn',
	'kimi-coding-cn': 'cn',
	stepfun: 'cn',
	minimax: 'cn',
	'minimax-cn': 'cn',
	// International (agrégateurs / hubs multi-origines)
	openrouter: 'intl',
	moa: 'intl',
	kilocode: 'intl',
	'opencode-zen': 'intl',
	'opencode-go': 'intl',
	novita: 'intl',
	gmi: 'intl',
	huggingface: 'intl',
	// Nouveaux fournisseurs natifs (plugins model-provider)
	mistral: 'eu', // 🇪🇺 souverain
	cohere: 'ca', // 🇨🇦 Canada
	groq: 'us',
	cerebras: 'us',
	together: 'us',
	fireworks: 'us',
	perplexity: 'us',
	'baidu-ernie': 'cn',
	// Sur-mesure : pas un pays -> pictogramme monde (🌍).
	custom: 'intl',
	// --- Autres onglets : Comptes (OAuth), Local, Autres ---
	// Comptes (connexion par compte / OAuth)
	nous: 'us',
	'openai-codex': 'us',
	'xai-oauth': 'us',
	'minimax-oauth': 'cn',
	'qwen-oauth': 'cn',
	// Local (modèles sur la machine du client) → souveraineté maximale
	lmstudio: 'local',
	'ollama-local': 'local',
	// Autres (authentification externe)
	'copilot-acp': 'us',
	bedrock: 'us'
};

export const getProviderGroup = (id?: string | null): ProviderGroup | null =>
	(id && GROUP_BY_ID[id]) || null;

export const getProviderRegion = (id?: string | null): ProviderRegion | null =>
	(id && REGION_BY_ID[id]) || null;

/** Drapeau à afficher sur la carte, ou null si origine inconnue. */
export const getProviderRegionFlag = (id?: string | null): string | null => {
	const r = getProviderRegion(id);
	return r ? REGION_FLAG[r] : null;
};

/** Nom complet de l'origine (pour l'infobulle), ou null si inconnue. */
export const getProviderRegionName = (id?: string | null): string | null => {
	const r = getProviderRegion(id);
	return r ? REGION_NAME[r] : null;
};

export type ProviderGroupBucket<T> = { key: string; label: string; items: T[] };

/**
 * Regroupe une liste de fournisseurs par GROUP, dans l'ordre officiel, les groupes
 * inconnus (« autres ») en fin de liste. Ne perd jamais un fournisseur.
 */
export function groupProviders<T extends { id: string }>(
	providers: T[]
): ProviderGroupBucket<T>[] {
	const byGroup = new Map<string, T[]>();
	for (const p of providers) {
		const g = getProviderGroup(p.id) ?? 'autres';
		if (!byGroup.has(g)) byGroup.set(g, []);
		byGroup.get(g)!.push(p);
	}

	const ordered: ProviderGroupBucket<T>[] = [];
	for (const g of GROUP_ORDER) {
		const items = byGroup.get(g);
		if (items) {
			ordered.push({ key: g, label: GROUP_LABEL[g], items });
			byGroup.delete(g);
		}
	}
	// Groupes non prévus (fournisseurs futurs non classés) : rangés en dernier.
	for (const [g, items] of byGroup) {
		ordered.push({ key: g, label: g === 'autres' ? 'Autres' : g, items });
	}
	return ordered;
}
