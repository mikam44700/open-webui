import {
	annulerOAuth,
	changerDeModele,
	deconnecterOAuth,
	demarrerOAuth,
	enregistrerCleFournisseur,
	getClesFournisseurs,
	getEtatDetaille,
	getEtatMoteur,
	getFournisseursCompte,
	getInfoModele,
	getNiveauIntelligence,
	getModelesCombines,
	getOptionsModeles,
	getServeursPersonnalises,
	retirerCleFournisseur,
	suivreOAuth,
	verifierCleFournisseur,
	definirNiveauIntelligence,
	verifierMiseAJour,
	demarrerMiseAJour,
	suivreMiseAJour
} from '$lib/apis/hermes';

type ProviderView = {
	id: string;
	label: string;
	logo: string;
	category: 'oauth' | 'api' | 'local' | 'other';
	state: 'active' | 'configured' | 'not_configured';
	env_key?: string | null;
	base_url?: string | null;
	endpoint_id?: string | null;
	models: { id: string; label: string }[];
	unavailable_reason?: string | null;
	/** Faux quand le compte est gere hors de Hermes et ne peut pas etre retire d'ici. */
	disconnectable?: boolean;
	disconnect_hint?: string | null;
	/** Commande a lancer soi-meme pour retirer un compte gere ailleurs. */
	disconnect_command?: string | null;
	/** Ou vit reellement la session : fichier, trousseau du systeme. */
	source_label?: string | null;
	/** 'device_code' | 'pkce' | 'external'. `external` se connecte par une commande. */
	flow?: string;
	cli_command?: string | null;
};

type ProviderMeta = {
	label: string;
	logo: string;
	category: ProviderView['category'];
	envKeys?: string[];
};

/**
 * Catalogue canonique Hermes v0.18.
 *
 * Les identifiants viennent de ``hermes_cli.provider_catalog``. Les logos sont
 * ceux de LunarIA / AgentOS V1 déjà livrés dans ``static/assets/providers``.
 * Les alias de variables d'environnement sont conservés dans l'ordre attendu
 * par chaque plugin Hermes : le premier sert lors d'une nouvelle connexion,
 * les suivants permettent de reconnaître une configuration existante.
 */
const PROVIDER_META: Record<string, ProviderMeta> = {
	nous: { label: 'Nous Research', logo: 'nous-research', category: 'oauth' },
	fireworks: {
		label: 'Fireworks AI',
		logo: 'fireworks-color',
		category: 'api',
		envKeys: ['FIREWORKS_API_KEY']
	},
	openrouter: {
		label: 'OpenRouter',
		logo: 'openrouter',
		category: 'api',
		envKeys: ['OPENROUTER_API_KEY']
	},
	moa: { label: 'Mixture of Agents', logo: 'api', category: 'api' },
	novita: { label: 'Novita AI', logo: 'novita', category: 'api', envKeys: ['NOVITA_API_KEY'] },
	lmstudio: {
		label: 'LM Studio',
		logo: 'lmstudio',
		category: 'local',
		envKeys: ['LM_API_KEY']
	},
	'ollama-local': {
		label: 'Ollama',
		logo: 'ollama',
		category: 'local'
	},
	anthropic: {
		label: 'Anthropic',
		logo: 'claude-color',
		category: 'api',
		envKeys: ['ANTHROPIC_API_KEY']
	},
	'openai-codex': { label: 'OpenAI Codex', logo: 'codex', category: 'oauth' },
	'openai-api': {
		label: 'OpenAI',
		logo: 'openai',
		category: 'api',
		envKeys: ['OPENAI_API_KEY']
	},
	alibaba: {
		label: 'Alibaba Cloud',
		logo: 'qwen',
		category: 'other',
		envKeys: ['DASHSCOPE_API_KEY']
	},
	'xai-oauth': { label: 'xAI', logo: 'grok', category: 'oauth' },
	xiaomi: { label: 'Xiaomi MiMo', logo: 'mimo', category: 'api', envKeys: ['XIAOMI_API_KEY'] },
	'tencent-tokenhub': {
		label: 'Tencent TokenHub',
		logo: 'tencent',
		category: 'api',
		envKeys: ['TOKENHUB_API_KEY']
	},
	nvidia: {
		label: 'NVIDIA NIM',
		logo: 'nvidia-color',
		category: 'api',
		envKeys: ['NVIDIA_API_KEY']
	},
	copilot: {
		label: 'GitHub Copilot',
		logo: 'copilot',
		category: 'other',
		envKeys: ['COPILOT_GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN']
	},
	'copilot-acp': { label: 'GitHub Copilot ACP', logo: 'copilot', category: 'other' },
	huggingface: {
		label: 'Hugging Face',
		logo: 'huggingface',
		category: 'api',
		envKeys: ['HF_TOKEN']
	},
	gemini: {
		label: 'Google Gemini',
		logo: 'gemini-color',
		category: 'api',
		envKeys: ['GOOGLE_API_KEY', 'GEMINI_API_KEY']
	},
	vertex: { label: 'Google Vertex AI', logo: 'vertex-color', category: 'other' },
	deepseek: {
		label: 'DeepSeek',
		logo: 'deepseek-color',
		category: 'api',
		envKeys: ['DEEPSEEK_API_KEY']
	},
	xai: { label: 'xAI', logo: 'grok', category: 'api', envKeys: ['XAI_API_KEY'] },
	zai: {
		label: 'Z.ai',
		logo: 'zai',
		category: 'api',
		envKeys: ['GLM_API_KEY', 'ZAI_API_KEY', 'Z_AI_API_KEY']
	},
	'kimi-coding': {
		label: 'Kimi Coding',
		logo: 'moonshot',
		category: 'api',
		envKeys: ['KIMI_API_KEY', 'KIMI_CODING_API_KEY']
	},
	'kimi-coding-cn': {
		label: 'Kimi Coding Chine',
		logo: 'moonshot',
		category: 'api',
		envKeys: ['KIMI_CN_API_KEY']
	},
	stepfun: { label: 'StepFun', logo: 'stepfun', category: 'api', envKeys: ['STEPFUN_API_KEY'] },
	minimax: {
		label: 'MiniMax',
		logo: 'minimax-color',
		category: 'api',
		envKeys: ['MINIMAX_API_KEY']
	},
	'minimax-oauth': { label: 'MiniMax', logo: 'minimax-color', category: 'oauth' },
	'minimax-cn': {
		label: 'MiniMax Chine',
		logo: 'minimax-color',
		category: 'api',
		envKeys: ['MINIMAX_CN_API_KEY']
	},
	'ollama-cloud': {
		label: 'Ollama Cloud',
		logo: 'ollama',
		category: 'api',
		envKeys: ['OLLAMA_API_KEY']
	},
	arcee: { label: 'Arcee AI', logo: 'arcee-color', category: 'api', envKeys: ['ARCEEAI_API_KEY'] },
	gmi: { label: 'GMI Cloud', logo: 'gmi', category: 'api', envKeys: ['GMI_API_KEY'] },
	kilocode: {
		label: 'Kilo Code',
		logo: 'kilocode',
		category: 'api',
		envKeys: ['KILOCODE_API_KEY']
	},
	'opencode-zen': {
		label: 'OpenCode Zen',
		logo: 'opencode',
		category: 'api',
		envKeys: ['OPENCODE_ZEN_API_KEY']
	},
	'opencode-go': {
		label: 'OpenCode Go',
		logo: 'opencode',
		category: 'api',
		envKeys: ['OPENCODE_GO_API_KEY']
	},
	bedrock: { label: 'AWS Bedrock', logo: 'bedrock-color', category: 'other' },
	'azure-foundry': {
		label: 'Azure AI Foundry',
		logo: 'azure',
		category: 'other',
		envKeys: ['AZURE_FOUNDRY_API_KEY']
	},
	'qwen-oauth': { label: 'Qwen', logo: 'qwen', category: 'oauth' },
	'alibaba-coding-plan': {
		label: 'Alibaba Coding Plan',
		logo: 'qwen',
		category: 'other',
		envKeys: ['ALIBABA_CODING_PLAN_API_KEY', 'DASHSCOPE_API_KEY']
	},
	custom: { label: 'Endpoint personnalisé', logo: 'custom', category: 'api' },
	deepinfra: {
		label: 'DeepInfra',
		logo: 'api',
		category: 'api',
		envKeys: ['DEEPINFRA_API_KEY']
	},
	upstage: { label: 'Upstage', logo: 'api', category: 'api', envKeys: ['UPSTAGE_API_KEY'] },
	'baidu-ernie': {
		label: 'Baidu ERNIE',
		logo: 'baidu-color',
		category: 'api',
		envKeys: ['BAIDU_API_KEY', 'QIANFAN_API_KEY']
	},
	cerebras: {
		label: 'Cerebras',
		logo: 'cerebras-color',
		category: 'api',
		envKeys: ['CEREBRAS_API_KEY']
	},
	cohere: { label: 'Cohere', logo: 'cohere-color', category: 'api', envKeys: ['COHERE_API_KEY'] },
	groq: { label: 'Groq', logo: 'groq-color', category: 'api', envKeys: ['GROQ_API_KEY'] },
	mistral: {
		label: 'Mistral AI',
		logo: 'mistral-color',
		category: 'api',
		envKeys: ['MISTRAL_API_KEY']
	},
	perplexity: {
		label: 'Perplexity',
		logo: 'perplexity-color',
		category: 'api',
		envKeys: ['PERPLEXITY_API_KEY']
	},
	sakana: {
		label: 'Sakana AI',
		logo: 'sakana-color',
		category: 'api',
		envKeys: ['SAKANA_API_KEY']
	},
	together: {
		label: 'Together AI',
		logo: 'together-color',
		category: 'api',
		envKeys: ['TOGETHER_API_KEY']
	}
};

/**
 * Fournisseurs que Hermes propose mais que l'on n'affiche pas.
 *
 * `claude-code` : cette voie ne donne PAS acces a un abonnement Claude. Hermes
 * l'ecrit lui-meme — elle « ne fonctionne qu'avec des credits d'usage
 * supplementaires, en plus d'un forfait Claude Max », d'ou le nom-avertissement
 * qu'il lui donne. La montrer comme un moyen de brancher son abonnement
 * induirait le client en erreur sur ce qu'il va payer. La connexion par cle
 * API Anthropic, elle, reste proposee : c'est la voie claire et sans surprise.
 */
const MASQUES = new Set(['claude-code']);

const envByProvider = new Map<string, string>();
let lastOptions: any = null;
const oauthSessions = new Map<string, { sessionId: string; started: boolean; log: string }>();

const modelsOf = (provider: any) =>
	(provider?.models ?? []).map((model: any) => {
		const id = typeof model === 'string' ? model : `${model.id ?? model.name ?? ''}`;
		return { id, label: typeof model === 'string' ? model : `${model.label ?? model.name ?? id}` };
	});

export const getProviders = async (token: string) => {
	envByProvider.clear();
	const [options, oauth, keys, endpoints, moaConfig] = await Promise.all([
		getOptionsModeles(token),
		getFournisseursCompte(token),
		getClesFournisseurs(token),
		getServeursPersonnalises(token).catch(() => ({ endpoints: [], current: {} })),
		getModelesCombines(token).catch(() => null)
	]);
	lastOptions = options;
	const currentProvider = `${options?.provider ?? ''}`;
	const optionList = options?.providers ?? [];
	const configured = new Map<string, any>(
		optionList.map((provider: any) => [`${provider.slug}`, provider])
	);
	const oauthById = new Map<string, any>(
		(oauth?.providers ?? []).map((provider: any) => [`${provider.id}`, provider])
	);
	const providers = new Map<string, ProviderView>();

	for (const option of optionList) {
		const id = `${option.slug}`;
		const meta = PROVIDER_META[id] ?? {
			label: `${option.label ?? option.name ?? id}`,
			logo: 'api',
			category: option.is_user_defined ? 'local' : 'api'
		};
		const account = oauthById.get(id);
		const envKey =
			meta.envKeys?.find((key) => Boolean(keys?.[key]?.is_set)) ?? meta.envKeys?.[0] ?? null;
		if (envKey) envByProvider.set(id, envKey);
		const hasStoredKey = Boolean(meta.envKeys?.some((key) => keys?.[key]?.is_set));
		const loggedIn = Boolean(account?.status?.logged_in);
		const authenticated = hasStoredKey || loggedIn || Boolean(option.authenticated);
		providers.set(id, {
			id,
			label: `${option.label ?? option.name ?? meta.label}`,
			logo: meta.logo,
			category: meta.category,
			state:
				authenticated && (currentProvider === id || option.is_current)
					? 'active'
					: authenticated
						? 'configured'
						: 'not_configured',
			env_key: envKey,
			base_url: option.base_url ?? null,
			models: modelsOf(option)
		});
	}

	// Ollama local est un serveur OpenAI-compatible, pas un fournisseur canonique
	// du catalogue Hermes. Il doit pourtant toujours être proposé à côté de
	// LM Studio, même avant sa première configuration.
	if (!providers.has('ollama-local')) {
		const endpointList = Array.isArray(endpoints?.endpoints) ? endpoints.endpoints : [];
		const ollamaEndpoint = endpointList.find((endpoint: any) => {
			const identity = `${endpoint?.id ?? endpoint?.name ?? ''}`.toLowerCase();
			const baseUrl = `${endpoint?.base_url ?? endpoint?.url ?? ''}`.toLowerCase();
			return identity.includes('ollama') || baseUrl.includes(':11434');
		});
		const endpointId = `${ollamaEndpoint?.id ?? ''}`;
		const currentEndpoint = `${
			endpoints?.current?.provider ?? options?.provider ?? ''
		}`.toLowerCase();
		const endpointModels = ollamaEndpoint?.models
			? Array.isArray(ollamaEndpoint.models)
				? ollamaEndpoint.models
				: Object.keys(ollamaEndpoint.models)
			: ollamaEndpoint?.model
				? [ollamaEndpoint.model]
				: [];
		const isActive =
			Boolean(ollamaEndpoint?.active ?? ollamaEndpoint?.is_current) ||
			Boolean(endpointId && currentEndpoint === endpointId.toLowerCase());

		providers.set('ollama-local', {
			id: 'ollama-local',
			label: 'Ollama',
			logo: 'ollama',
			category: 'local',
			state: isActive ? 'active' : ollamaEndpoint ? 'configured' : 'not_configured',
			base_url:
				ollamaEndpoint?.base_url ?? ollamaEndpoint?.url ?? 'http://host.docker.internal:11434/v1',
			endpoint_id: endpointId || null,
			models: endpointModels.map((model: any) => {
				const id = typeof model === 'string' ? model : `${model?.id ?? model?.name ?? ''}`;
				return { id, label: id };
			})
		});
	}

	// Un compte OAuth peut être exposé par Hermes avant que son plugin modèle ne
	// fournisse des options. On conserve donc aussi ces cartes, sans doublon.
	for (const account of oauth?.providers ?? []) {
		const id = `${account.id}`;
		if (providers.has(id) || MASQUES.has(id)) continue;
		const meta = PROVIDER_META[id] ?? {
			label: `${account.name ?? id}`,
			logo: 'api',
			category: 'oauth' as const
		};
		providers.set(id, {
			id,
			// Le libelle du catalogue prime quand on en a un : les noms renvoyes par
			// Hermes sont parfois des phrases entieres, illisibles sur une carte.
			label: PROVIDER_META[id] ? meta.label : `${account.name ?? meta.label}`,
			logo: meta.logo,
			category: meta.category,
			state: account.status?.logged_in ? 'configured' : 'not_configured',
			models: [],
			// Certains comptes sont reconnus par Hermes mais gardes ailleurs — la
			// session de Claude Code, par exemple, vit dans le trousseau du systeme.
			// Hermes le signale ; sans ces trois champs, l'ecran proposait un bouton
			// « Deconnecter » qui ne pouvait qu'echouer, sans dire quoi faire.
			disconnectable: account.disconnectable !== false,
			disconnect_hint: account.disconnect_hint ?? null,
			disconnect_command: account.disconnect_command ?? null,
			source_label: account.status?.source_label ?? null,
			// `external` = la connexion se fait par une commande, hors de cet ecran.
			// Sans cette information, on affichait un bouton « Se connecter » qui ne
			// pouvait rien declencher.
			flow: `${account.flow ?? ''}`,
			cli_command: account.cli_command ?? null
		});
	}

	if (!providers.has('moa')) {
		providers.set('moa', {
			id: 'moa',
			label: 'Mixture of Agents',
			logo: 'api',
			category: 'api',
			state: 'not_configured',
			models: [{ id: 'default', label: 'Configuration MoA' }]
		});
	}

	// MoA n'est pas un fournisseur autonome : il ne peut répondre que si son
	// agrégateur ET tous ses modèles de référence actifs sont eux-mêmes branchés.
	// Hermes le déclare comme virtuel/authentifié, ce qui le faisait apparaître
	// à tort dans le chat alors qu'OpenRouter (dans la configuration actuelle)
	// n'avait aucune clé.
	const moa = providers.get('moa');
	if (moa) {
		const aggregator = `${moaConfig?.aggregator?.provider ?? ''}`;
		const references = Array.isArray(moaConfig?.reference_models)
			? moaConfig.reference_models.filter((slot: any) => slot?.enabled !== false)
			: [];
		const dependencyIds = [
			aggregator,
			...references.map((slot: any) => `${slot?.provider ?? ''}`)
		].filter((id, index, all) => id && id !== 'moa' && all.indexOf(id) === index);
		const isUsable = (id: string) => {
			const dependency = providers.get(id);
			return Boolean(
				dependency && dependency.state !== 'not_configured' && (dependency.models?.length ?? 0) > 0
			);
		};
		const missingIds = dependencyIds.filter((id) => !isUsable(id));
		const usable =
			Boolean(moaConfig?.enabled) &&
			Boolean(aggregator) &&
			references.length > 0 &&
			missingIds.length === 0;

		if (usable) {
			moa.state = currentProvider === 'moa' ? 'active' : 'configured';
			moa.unavailable_reason = null;
		} else {
			const missingLabels = missingIds.map(
				(id) => providers.get(id)?.label ?? PROVIDER_META[id]?.label ?? id
			);
			moa.state = 'not_configured';
			moa.unavailable_reason = !moaConfig?.enabled
				? 'Active MoA dans Modèles IA avant de l’utiliser dans le chat.'
				: missingLabels.length > 0
					? `Connecte ${missingLabels.join(', ')} pour utiliser MoA dans le chat.`
					: 'Configure l’agrégateur et les modèles de référence de MoA avant de l’utiliser.';
		}
	}

	return { providers: [...providers.values()] };
};

export const getActiveProvider = async (token: string) => {
	const info = await getInfoModele(token);
	return { provider_id: info?.provider ?? '', model_id: info?.model ?? '' };
};

export const setActiveProvider = (token: string, providerId: string, modelId: string) =>
	changerDeModele(token, modelId, providerId);

export const getModelCapabilities = async (token: string, providerId: string, modelId: string) => {
	if (!lastOptions) lastOptions = await getOptionsModeles(token);
	const provider = lastOptions?.providers?.find((item: any) => item.slug === providerId);
	const caps = provider?.capabilities?.[modelId] ?? {};
	const current = await getInfoModele(token).catch(() => ({}));
	return {
		reasoning: caps.reasoning ?? null,
		vision: current?.provider === providerId ? current?.capabilities?.supports_vision : null,
		tools: current?.provider === providerId ? current?.capabilities?.supports_tools : null,
		context_window: current?.provider === providerId ? current?.effective_context_length : null,
		// Hermes accepte ces quatre efforts par requête via model_options. Les exposer ici
		// restaure exactement les quatre niveaux du chat LunarIA V1, tout en laissant le
		// runtime fournisseur appliquer son équivalent natif.
		supported_efforts: caps.reasoning === false ? [] : ['low', 'medium', 'high', 'xhigh'],
		effort_confidence: 'hermes_runtime'
	};
};

export const getReasoning = (token: string) => getNiveauIntelligence(token);
export const setReasoning = (token: string, effort: string) =>
	definirNiveauIntelligence(token, effort);

export const setProviderKey = async (token: string, providerId: string, value: string) => {
	const key = envByProvider.get(providerId);
	if (!key) throw new Error('Hermes ne déclare pas de clé pour ce fournisseur.');
	await enregistrerCleFournisseur(token, key, value);
	return { ok: true };
};

export const validateProviderKey = async (token: string, providerId: string, value: string) => {
	const key = envByProvider.get(providerId);
	if (!key) throw new Error('Hermes ne déclare pas de clé pour ce fournisseur.');
	const result = await verifierCleFournisseur(token, key, value);
	return { ...result, valid: result?.ok === true };
};

export const deleteProviderKey = async (token: string, providerId: string) => {
	const key = envByProvider.get(providerId);
	if (!key) throw new Error('Hermes ne déclare pas de clé pour ce fournisseur.');
	await retirerCleFournisseur(token, key);
	return { ok: true };
};

export const setAwsCredentials = async (
	token: string,
	_providerId: string,
	creds: { access_key_id: string; secret_access_key: string; region?: string }
) => {
	await Promise.all([
		enregistrerCleFournisseur(token, 'AWS_ACCESS_KEY_ID', creds.access_key_id),
		enregistrerCleFournisseur(token, 'AWS_SECRET_ACCESS_KEY', creds.secret_access_key),
		enregistrerCleFournisseur(token, 'AWS_REGION', creds.region ?? 'us-east-1')
	]);
	return { ok: true };
};

export const startProviderOAuth = async (token: string, providerId: string) => {
	const result = await demarrerOAuth(token, providerId);
	const sessionId = `${result?.session_id ?? result?.id ?? ''}`;
	// Meme oubli que dans PanneauComptes : `verification_url` est le nom
	// qu'emploie Hermes pour le flux « device code ». Sans lui, aucune fenetre
	// d'autorisation ne s'ouvre et la connexion ne peut jamais aboutir.
	const url =
		result?.verification_uri_complete ??
		result?.verification_url ??
		result?.verification_uri ??
		result?.authorization_url ??
		result?.auth_url ??
		result?.url;
	const userCode = result?.user_code ? `Code : ${result.user_code}` : '';
	if (url && typeof window !== 'undefined') window.open(url, '_blank', 'noopener,noreferrer');
	oauthSessions.set(providerId, { sessionId, started: true, log: userCode });
	return result;
};

export const getProviderOAuthStatus = async (token: string, providerId: string) => {
	const session = oauthSessions.get(providerId);
	if (!session?.sessionId) return { started: false, running: false, success: false, log: '' };
	const result = await suivreOAuth(token, providerId, session.sessionId);
	const status = `${result?.status ?? ''}`.toLowerCase();
	const success = ['approved', 'connected', 'complete', 'completed', 'success'].includes(status);
	const failed = ['error', 'denied', 'expired', 'cancelled'].includes(status);
	if (success || failed) oauthSessions.delete(providerId);
	return {
		started: true,
		running: !success && !failed,
		success,
		log: result?.error_message ?? session.log
	};
};

export const logoutProviderOAuth = async (token: string, providerId: string) => {
	const session = oauthSessions.get(providerId);
	if (session?.sessionId) await annulerOAuth(token, session.sessionId).catch(() => null);
	oauthSessions.delete(providerId);
	return deconnecterOAuth(token, providerId);
};

export const getHermesStatus = async (token: string) => {
	const [health, status, active] = await Promise.all([
		getEtatMoteur(token),
		getEtatDetaille(token),
		getInfoModele(token).catch(() => null)
	]);
	const providerId = active?.provider ?? health?.fournisseur_actif ?? '';
	const modelId = active?.model ?? health?.modele_actif ?? '';
	const reachable = Boolean(health?.joignable);

	return {
		installed: true,
		running: reachable,
		// Format attendu par le panneau Agent Hermes repris de LunarIA V1.
		// Avant cette adaptation, la V2 renvoyait uniquement `running` et le
		// panneau cherchait `hermes_available` : il affichait donc une fausse panne.
		hermes_available: reachable,
		api_server: {
			reachable,
			port: 8642
		},
		brain_connected: Boolean(providerId && modelId && providerId !== 'auto'),
		active: {
			provider_id: providerId,
			model_id: modelId
		},
		active_provider_label: active?.provider_label ?? providerId,
		version: status?.version ?? health?.version ?? '',
		current_version: status?.version ?? '',
		latest_version: status?.version ?? '',
		update_available: false,
		gateway_running: status?.gateway_running ?? true
	};
};

/**
 * Mise a jour du moteur.
 *
 * Ces trois fonctions etaient des coquilles vides : le bouton « Mettre a jour »
 * ne faisait rien et « Verifier » repondait toujours « a jour ». Elles sont
 * desormais branchees sur l'API de Hermes, qui se met a jour lui-meme.
 *
 * Cela marche quel que soit l'endroit ou tourne le moteur — a cote d'ici, ou
 * dans son propre conteneur sur un serveur : on ne lance jamais de commande,
 * on le lui demande. Hermes repond `can_apply: false` quand son mode
 * d'installation lui interdit de s'appliquer la mise a jour tout seul, et
 * donne alors la marche a suivre dans `message`.
 */
export const checkHermesUpdate = async (token: string) => {
	const r = await verifierMiseAJour(token);

	// Une verification qui n'a pas pu aboutir (hors-ligne, depot injoignable)
	// renvoie `behind: null`. On ne la fait pas passer pour « a jour » : le
	// panneau doit pouvoir dire « verification impossible » plutot que mentir.
	const verificationAboutie = r?.behind !== null && r?.behind !== undefined;
	const retard = verificationAboutie ? Number(r.behind) : 0;

	const details = [
		r?.message,
		r?.update_command ? `Commande : ${r.update_command}` : '',
		...(r?.commits ?? []).slice(0, 10).map((c) => `${c.sha?.slice(0, 7)} ${c.summary}`)
	].filter(Boolean);

	return {
		output: details.join('\n'),
		available: Boolean(r?.update_available) && retard !== 0,
		can_apply: r?.can_apply ?? false,
		install_method: r?.install_method ?? 'unknown',
		current_version: verificationAboutie ? (r?.current_version ?? '') : '',
		latest_version: ''
	};
};

export const startHermesUpdate = async (token: string) => {
	const r = await demarrerMiseAJour(token);
	if (r && r.ok === false) {
		throw new Error(r.message ?? 'Mise a jour indisponible pour ce mode d installation.');
	}
	return r;
};

export const getHermesUpdateStatus = async (token: string) => {
	const r = await suivreMiseAJour(token);
	const enCours = Boolean(r?.running);
	const lignes = r?.lines ?? [];
	const code = r?.exit_code;
	const journal = lignes.join('\n');
	const demarree = enCours || lignes.length > 0;

	if (enCours || !demarree) {
		return {
			running: enCours,
			started: demarree,
			success: false,
			rolled_back: false,
			log: journal
		};
	}

	// La mise a jour est terminee. Une mise a jour REUSSIE redemarre les services
	// de Hermes — le suivi perd alors le code de sortie du processus et renvoie
	// `null`. S'y fier ferait tourner la page en boucle sans jamais annoncer la
	// fin. On tranche donc sur un fait verifiable : reste-t-il quelque chose a
	// installer ?
	const succes =
		code === 0
			? true
			: code === null || code === undefined
				? await verifierMiseAJour(token)
						.then((v) => v?.update_available === false)
						.catch(() => false)
				: false;

	return { running: false, started: true, success: succes, rolled_back: false, log: journal };
};
