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
export type ProviderRegion = 'us' | 'cn' | 'eu' | 'fr' | 'ca' | 'jp' | 'intl' | 'local';

/**
 * Fournisseurs « multi-agents » (cerveaux combinés) : affichés dans l'onglet dédié
 * « Cerveaux combinés », et EXCLUS de l'onglet « Clés API » pour éviter le doublon.
 * - sakana : système multi-agents livré comme un seul modèle (clé simple).
 * - moa : Mixture of Agents, technique interne du moteur (config des modèles à combiner).
 */
export const MULTIAGENT_IDS = new Set<string>(['sakana', 'moa']);

/**
 * Fournisseurs de « Clés API » masqués par défaut, révélés uniquement en mode Expert
 * (Réglages avancés). Choix produit : ne présenter au dirigeant non-tech que les
 * fournisseurs courants ; les spécialisés / techniques restent accessibles mais
 * discrets. Aucune fonction retirée — seulement la visibilité, et c'est réversible.
 */
export const EXPERT_PROVIDER_IDS = new Set<string>([
	'copilot', // GitHub Copilot
	'vertex', // Google Vertex
	'nvidia', // NVIDIA NIM — free tier « pour tester » seulement (prod = NVIDIA AI Enterprise,
	//            cher) + ~40 req/min + catalogue plein de fantômes. Réservé aux avertis.
	'cohere', // Cohere
	'kilocode', // Kilo Code
	'opencode-zen', // OpenCode (Zen)
	'opencode-go', // OpenCode (Go)
	'novita', // NovitaAI
	'arcee', // Arcee AI
	'gmi', // GMI Cloud
	'cerebras', // Cerebras
	'fireworks', // Fireworks AI
	'groq', // Groq
	'together', // Together AI
	'xiaomi', // Xiaomi
	'tencent-tokenhub', // Tencent
	'stepfun', // StepFun
	'baidu-ernie', // Baidu ERNIE
	'huggingface', // Hugging Face (Clés API)
	// alibaba / alibaba-coding-plan : déplacés dans l'onglet « Autres » (Category.other côté bridge,
	// à côté d'AWS Bedrock / Azure — cloud entreprise, 2026-07-08). Conservés ici (inoffensif :
	// l'onglet « Autres » est déjà expert-only) pour rester réversible sans régression.
	'alibaba', // Qwen Cloud → onglet « Autres »
	'alibaba-coding-plan', // Qwen Coding Plan → onglet « Autres »
	'qwen-oauth', // Qwen (Comptes / OAuth)
	'minimax-cn', // MiniMax — endpoint Chine (doublon de `minimax` international)
	'kimi-coding-cn', // Kimi / Moonshot — endpoint Chine (doublon de `kimi-coding`)
	'custom' // Sur-mesure (endpoint personnalisé)
]);

/** Vrai si le fournisseur n'apparaît qu'en mode Expert (Réglages avancés). */
export const isExpertProvider = (id?: string | null): boolean =>
	!!id && EXPERT_PROVIDER_IDS.has(id);

/**
 * Fournisseurs masqués TOTALEMENT (même en mode Expert) : service fermé / discontinué
 * côté fournisseur, donc trompeur pour le client (connexion acceptée mais requêtes
 * rejetées). Réversible — retirer l'id d'ici le réaffiche. Aucune fonction moteur retirée.
 */
export const HIDDEN_PROVIDER_IDS = new Set<string>([
	// Qwen OAuth : free tier fermé par Alibaba le 2026-04-15 (login accepté mais 429).
	// Remplacé par les clés `alibaba` / `alibaba-coding-plan`, qui restent visibles.
	'qwen-oauth',
	// Perplexity Sonar : answer engine incompatible avec le chat agentique Hermes.
	// Aucun modèle Sonar ne supporte le tool calling → HTTP 400 dès qu'un outil est
	// actif (sonar ET sonar-reasoning-pro testés E2E le 2026-07-06, les deux plantent).
	// Sa seule valeur (recherche web sourcée) fait doublon avec la recherche web NATIVE
	// de Hermes (Tavily/Exa/Brave/DDG + web_extract), disponible sur tous les modèles
	// agentiques. Masqué, pas supprimé : le plugin reste (réversible si Perplexity ouvre
	// le tool calling un jour). Cf. commit dd877cf.
	'perplexity',
	// Google Vertex AI : mêmes modèles Gemini que la carte `gemini` (clé AI Studio simple),
	// mais auth « entreprise » Google Cloud (compte de service JSON + project_id + region +
	// facturation GCP) → inaccessible à un dirigeant non-tech, et redondant. La carte
	// affichait en plus un champ « clé API » qui ne peut pas fonctionner (Vertex n'a pas de
	// clé API) + 0 modèle listé. Masqué, pas supprimé (moteur v0.18 le supporte : réversible
	// le jour où un vrai client entreprise déjà sur GCP le réclame — cf. agent/vertex_adapter.py).
	'vertex',
	// GitHub Copilot : pas de vraie clé API — auth = token GitHub / device flow OAuth +
	// abonnement Copilot mensuel personnel. Trop complexe pour la cible non-tech (décision
	// 2026-07-07 : le « bouton magique » OAuth envisagé est abandonné). Masqué, pas supprimé
	// (moteur le supporte : réversible). `copilot-acp` (cas technique, login CLI machine)
	// masqué aussi pour ne laisser aucune trace Copilot à l'écran.
	'copilot',
	'copilot-acp',
	// Endpoints Chine (doublons des cartes internationales) : mêmes modèles que `kimi-coding`
	// et `minimax` mais routés vers les serveurs chinois (api.moonshot.cn / api.minimaxi.com CN).
	// Redondants et sans intérêt pour la cible → masqués (2026-07-08). Plugins conservés,
	// réversible. Les cartes internationales `kimi-coding` et `minimax`/`minimax-oauth` restent.
	'kimi-coding-cn',
	'minimax-cn',
	// Nouveaux venus du moteur v0.18.2 (jamais présents en V1) : sans fiche curée ils
	// tombaient dans la section fourre-tout « AUTRES » avec une carte brouillonne
	// (« 0 modèles », logo générique). Aucun intérêt pour la cible dirigeant non-tech.
	// Masqués (2026-07-18, chantier restauration providers V1), pas supprimés : retirer
	// l'id d'ici + ajouter une fiche PROVIDER_INFO suffit pour les réactiver.
	'deepinfra', // hébergeur US de modèles open-source, paiement à l'usage
	'upstage' // Upstage Solar — boîte d'IA coréenne
]);

/** Vrai si le fournisseur est masqué partout, y compris en mode Expert. */
export const isHiddenProvider = (id?: string | null): boolean =>
	!!id && HIDDEN_PROVIDER_IDS.has(id);

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
	// azure-foundry : PAS ici — rangé dans l'onglet « Autres » (auth externe, à côté d'AWS
	// Bedrock) via sa Category.other côté bridge (cf. hermes_adapter._category). Cloud entreprise
	// à endpoint + déploiements requis, pas un hébergeur clé-en-main → hors onglet « Clés API ».
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
	// Sur-mesure : endpoint personnalisé + MoA (technique interne, pas un vrai fournisseur)
	custom: 'custom',
	moa: 'custom'
};

/** Drapeau / pictogramme affiché sur la carte (léger). */
export const REGION_FLAG: Record<ProviderRegion, string> = {
	us: '🇺🇸',
	cn: '🇨🇳',
	eu: '🇪🇺',
	fr: '🇫🇷',
	ca: '🇨🇦',
	jp: '🇯🇵',
	intl: '🌍',
	local: '💻'
};

/** Nom complet, montré au survol (infobulle) pour rester clair. */
export const REGION_NAME: Record<ProviderRegion, string> = {
	us: 'États-Unis',
	cn: 'Chine',
	eu: 'Europe',
	fr: 'France',
	ca: 'Canada',
	jp: 'Japon',
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
	mistral: 'fr', // 🇫🇷 France (origine) — « champion européen » reste dans la description
	cohere: 'ca', // 🇨🇦 Canada
	groq: 'us',
	cerebras: 'us',
	together: 'us',
	fireworks: 'us',
	perplexity: 'us',
	'baidu-ernie': 'cn',
	sakana: 'jp', // 🇯🇵 Sakana AI (Japon)
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
