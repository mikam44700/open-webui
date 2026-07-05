// Infos « client » des fournisseurs de modèles IA (page Modèles IA) : phrase grise courte,
// déroulant « Voir ce que ça fait », lien « Obtenir la clé » (keyUrl : page officielle où
// récupérer sa clé API) et lien « Voir mon usage » (usageUrl : page officielle du fournisseur
// où voir son quota / sa consommation). Clé = identifiant Hermes du fournisseur (source : bridge hermes_adapter).
// Un id absent retombe proprement (pas de desc dédiée, pas de lien).
//
// Règle rédaction (pour un dirigeant non-tech) : desc = 1 phrase « qui c'est + pour quoi »,
// about = 2 puces concrètes (ce qu'on obtient + quand c'est le bon choix). Zéro jargon nu.

export type ProviderInfo = {
	desc?: string;
	about?: string[];
	keyUrl?: string;
	usageUrl?: string;
};

export const PROVIDER_INFO: Record<string, ProviderInfo> = {
	// ── Les grands noms ───────────────────────────────────────
	'openai-api': {
		desc: 'Les modèles GPT d’OpenAI (les créateurs de ChatGPT).',
		keyUrl: 'https://platform.openai.com/api-keys',
		about: [
			'Excellents pour le raisonnement, la rédaction et le code',
			'La référence du marché — facturation à l’usage'
		]
	},
	'openai-codex': {
		desc: 'GPT-5.5 via votre abonnement OpenAI Codex.',
		about: [
			'Réutilise votre compte ChatGPT / Codex, sans nouvelle clé',
			'Idéal si vous payez déjà OpenAI'
		],
		usageUrl: 'https://chatgpt.com/codex/cloud/settings/analytics'
	},
	anthropic: {
		desc: 'Les modèles Claude d’Anthropic.',
		keyUrl: 'https://console.anthropic.com/settings/keys',
		about: [
			'Excellents en analyse, rédaction longue et code',
			'Réputés fiables et prudents — qualité premium'
		]
	},
	gemini: {
		desc: 'Les modèles Gemini de Google (AI Studio).',
		keyUrl: 'https://aistudio.google.com/app/apikey',
		about: [
			'Rapides et multimodaux (texte, image, audio, vidéo)',
			'Offre gratuite généreuse pour démarrer sans carte'
		]
	},
	google: {
		desc: 'Google AI Studio — les modèles Gemini.',
		keyUrl: 'https://aistudio.google.com/app/apikey',
		about: [
			'Accès direct aux modèles Gemini de Google',
			'Offre gratuite pour tester sans engagement'
		]
	},
	mistral: {
		desc: 'Mistral AI — le champion européen 🇪🇺.',
		keyUrl: 'https://console.mistral.ai/api-keys',
		about: [
			'Modèles souverains, entreprise française',
			'Bon rapport qualité/prix, à l’aise en français et en code'
		]
	},
	vertex: {
		desc: 'Les modèles Gemini via Google Cloud (entreprise).',
		keyUrl: 'https://console.cloud.google.com/vertex-ai',
		about: [
			'Les mêmes modèles Gemini, côté Google Cloud',
			'Pour les entreprises déjà sur GCP (facturation unifiée)'
		]
	},
	deepseek: {
		desc: 'DeepSeek — très puissant et parmi les moins chers.',
		keyUrl: 'https://platform.deepseek.com/api_keys',
		about: [
			'Excellent en raisonnement et en code',
			'Un des meilleurs rapports qualité/prix du marché'
		]
	},
	xai: {
		desc: 'Les modèles Grok de xAI (l’IA d’Elon Musk).',
		keyUrl: 'https://console.x.ai',
		about: [
			'Ton direct, à l’aise avec l’actualité et la culture web',
			'Recherche web en temps réel intégrée'
		]
	},
	cohere: {
		desc: 'Cohere — spécialiste entreprise et documents.',
		keyUrl: 'https://dashboard.cohere.com/api-keys',
		about: [
			'Fort pour interroger VOS documents (recherche intelligente)',
			'Modèles Command, pensés pour le monde pro'
		]
	},
	perplexity: {
		desc: 'Perplexity Sonar — l’IA qui cherche sur le web.',
		keyUrl: 'https://www.perplexity.ai/settings/api',
		about: [
			'Répond en direct en citant ses sources',
			'Idéal pour l’actualité, la veille et la recherche'
		]
	},
	copilot: {
		desc: 'GitHub Copilot — l’assistant des développeurs.',
		keyUrl: 'https://github.com/settings/tokens',
		about: [
			'Pensé avant tout pour le code',
			'Nécessite un abonnement GitHub Copilot (forfait mensuel)'
		]
	},

	// ── Cerveaux combinés (multi-agents) ──────────────────────
	sakana: {
		desc: 'Sakana Fugu — plusieurs cerveaux en un seul, prêt à l’emploi.',
		keyUrl: 'https://console.sakana.ai',
		about: [
			'Un système multi-agents livré comme UN seul modèle : il assemble tout seul une équipe d’IA selon la difficulté',
			'Zéro réglage : tu entres ta clé, ça marche dans le chat (variantes « fugu » rapide et « fugu-ultra » qualité max)',
			'Au choix : paiement à l’usage OU abonnement mensuel (Standard / Pro / Max)'
		]
	},

	// ── Une seule clé, plein de modèles (passerelles) ─────────
	openrouter: {
		desc: 'Une seule clé pour des centaines de modèles.',
		keyUrl: 'https://openrouter.ai/keys',
		about: [
			'Accédez à OpenAI, Claude, Llama… via un seul compte',
			'Idéal pour comparer les modèles et optimiser les coûts'
		]
	},
	moa: {
		desc: 'Combine plusieurs modèles pour une meilleure réponse (technique, pas un fournisseur).',
		about: [
			'Interroge plusieurs modèles et fusionne leurs réponses',
			'Intégré au moteur — pas une marque, pas de site dédié'
		]
	},
	kilocode: {
		desc: 'Kilo Code — passerelle multi-modèles pour le code.',
		keyUrl: 'https://app.kilocode.ai',
		about: [
			'Un seul accès à plusieurs modèles de programmation',
			'Basculez d’un modèle à l’autre sans multiplier les clés'
		]
	},
	'opencode-zen': {
		desc: 'OpenCode Zen — passerelle multi-modèles.',
		keyUrl: 'https://opencode.ai/',
		about: [
			'Un seul compte pour accéder à plusieurs modèles',
			'Pratique pour tester sans créer 10 comptes'
		]
	},
	'opencode-go': {
		desc: 'OpenCode Go — passerelle multi-modèles.',
		keyUrl: 'https://opencode.ai/',
		about: [
			'Un seul compte pour accéder à plusieurs modèles',
			'Alternative légère pour jongler entre plusieurs IA'
		]
	},

	// ── Plateformes d’hébergement (open source / infra) ───────
	novita: {
		desc: 'NovitaAI — modèles open source hébergés, pas chers.',
		keyUrl: 'https://novita.ai/settings/key-management',
		about: [
			'Faites tourner Llama, DeepSeek… sans gérer de serveur',
			'Facturation à l’usage, économique'
		]
	},
	nvidia: {
		desc: 'NVIDIA NIM — modèles open source optimisés.',
		keyUrl: 'https://build.nvidia.com',
		about: [
			'Modèles ouverts servis sur l’infrastructure NVIDIA',
			'Inférence optimisée, prête pour l’entreprise'
		]
	},
	huggingface: {
		desc: 'Hugging Face — la plus grande bibliothèque de modèles ouverts.',
		keyUrl: 'https://huggingface.co/settings/tokens',
		about: [
			'Des milliers de modèles open source via un seul compte',
			'Parfait pour explorer au-delà des grands noms'
		]
	},
	'ollama-cloud': {
		desc: 'Ollama Cloud — vos modèles ouverts dans le cloud.',
		keyUrl: 'https://ollama.com/settings/keys',
		about: [
			'La simplicité d’Ollama, sans mobiliser votre machine',
			'Pour faire tourner des modèles ouverts à distance'
		]
	},
	arcee: {
		desc: 'Arcee AI — petits modèles spécialisés et efficaces.',
		keyUrl: 'https://models.arcee.ai',
		about: [
			'Modèles compacts, taillés pour l’entreprise',
			'Bon compromis entre performance et coût'
		]
	},
	gmi: {
		desc: 'GMI Cloud — modèles open source hébergés.',
		keyUrl: 'https://console.gmicloud.ai/',
		about: [
			'Faites tourner des modèles ouverts sans infra à gérer',
			'Facturation à l’usage, économique'
		]
	},
	'azure-foundry': {
		desc: 'Azure AI Foundry — l’IA côté Microsoft.',
		keyUrl: 'https://ai.azure.com',
		about: [
			'Modèles hébergés sur le cloud Azure',
			'Pour les entreprises déjà chez Microsoft'
		]
	},
	groq: {
		desc: 'Groq — inférence ultra-rapide.',
		keyUrl: 'https://console.groq.com/keys',
		about: [
			'Réponses très rapides sur modèles open source (Llama…)',
			'Bon marché'
		]
	},
	cerebras: {
		desc: 'Cerebras — la vitesse record.',
		keyUrl: 'https://cloud.cerebras.ai/',
		about: [
			'Réponses quasi instantanées (puce dédiée à l’IA)',
			'Idéal quand la rapidité prime'
		]
	},
	together: {
		desc: 'Together AI — grand catalogue de modèles ouverts.',
		keyUrl: 'https://api.together.ai/',
		about: [
			'Llama, DeepSeek, Qwen et bien d’autres au même endroit',
			'Bon rapport qualité/prix'
		]
	},
	fireworks: {
		desc: 'Fireworks AI — modèles ouverts rapides et pas chers.',
		keyUrl: 'https://fireworks.ai/account/api-keys',
		about: [
			'Llama, DeepSeek et autres modèles ouverts',
			'Bon équilibre entre vitesse et prix'
		]
	},

	// ── Modèles chinois ───────────────────────────────────────
	alibaba: {
		desc: 'Qwen — les modèles d’Alibaba, très polyvalents.',
		keyUrl: 'https://bailian.console.alibabacloud.com',
		about: [
			'Bons généralistes, multilingues et doués en code',
			'Du petit modèle rapide au très puissant'
		]
	},
	'alibaba-coding-plan': {
		desc: 'Qwen — forfait spécial code (Alibaba).',
		keyUrl: 'https://bailian.console.alibabacloud.com',
		about: [
			'Les modèles Qwen optimisés pour la programmation',
			'Abonnement mensuel à prix fixe (forfait « Qwen Code »), pas de facturation au token'
		]
	},
	xiaomi: {
		desc: 'Xiaomi MiMo — modèles ouverts de Xiaomi.',
		keyUrl: 'https://platform.xiaomimimo.com',
		about: [
			'Modèles légers, orientés raisonnement',
			'Alternative open source économique'
		]
	},
	'tencent-tokenhub': {
		desc: 'Tencent TokenHub — l’IA du géant Tencent.',
		keyUrl: 'https://console.cloud.tencent.com/hunyuan/api-key',
		about: [
			'Accès aux modèles Hunyuan de Tencent',
			'Hébergé par l’un des plus grands groupes chinois'
		]
	},
	zai: {
		desc: 'Z.AI — les modèles GLM (Zhipu AI).',
		keyUrl: 'https://z.ai/manage-apikey/apikey-list',
		about: [
			'Bons généralistes, forts en chinois et en code',
			'Rapport qualité/prix intéressant',
			'Aussi disponible en abonnement mensuel : « GLM Coding Plan »'
		]
	},
	'kimi-coding': {
		desc: 'Kimi (Moonshot) — champion du contexte long.',
		keyUrl: 'https://platform.moonshot.ai/console/api-keys',
		about: [
			'Avale des documents entiers d’un seul coup',
			'Aussi disponible en abonnement mensuel : « Kimi Code »'
		]
	},
	'kimi-coding-cn': {
		desc: 'Kimi (Moonshot) — accès depuis la Chine.',
		keyUrl: 'https://platform.moonshot.cn/console/api-keys',
		about: [
			'Les mêmes modèles Kimi, serveurs en Chine',
			'Très grande fenêtre de contexte',
			'Aussi disponible en abonnement mensuel (Coding Plan)'
		]
	},
	minimax: {
		desc: 'MiniMax — IA de conversation, aussi voix et vidéo.',
		keyUrl: 'https://www.minimax.io/platform',
		about: [
			'Modèle de chat (LLM), en plus voix et vidéo',
			'Économique'
		]
	},
	'minimax-cn': {
		desc: 'MiniMax — accès depuis la Chine.',
		keyUrl: 'https://platform.minimaxi.com',
		about: [
			'Les mêmes modèles MiniMax, serveurs en Chine',
			'Multimodal (texte + audio)'
		]
	},
	stepfun: {
		desc: 'StepFun — modèles multimodaux chinois.',
		keyUrl: 'https://platform.stepfun.com/',
		about: [
			'À l’aise en texte et en image',
			'Forfait Step Plan'
		]
	},
	'baidu-ernie': {
		desc: 'Baidu ERNIE — les grands modèles de Baidu.',
		keyUrl: 'https://console.bce.baidu.com/iam/#/iam/apikey',
		about: [
			'Modèles ERNIE 4.5 / X1, très forts en chinois',
			'Via la plateforme Qianfan (compatible OpenAI)'
		]
	},

	// ── Comptes (OAuth) ───────────────────────────────────────
	'xai-oauth': {
		desc: 'Grok via votre compte X (SuperGrok / Premium+).',
		about: [
			'Réutilise votre abonnement X, sans clé à saisir',
			'Pratique si vous êtes déjà abonné'
		],
		usageUrl: 'https://grok.com/settings/usage'
	},
	'minimax-oauth': {
		desc: 'MiniMax via votre compte.',
		about: ['Connexion par compte, sans clé à saisir', 'Multimodal (texte + audio)'],
		usageUrl: 'https://platform.minimax.io/user-center/payment/balance'
	},
	'qwen-oauth': {
		desc: 'Qwen via votre compte (Portal).',
		about: ['Connexion par compte, sans clé à saisir', 'Accès aux modèles Qwen d’Alibaba']
	},
	nous: {
		desc: 'Nous Portal — les modèles de Nous Research.',
		about: ['Connexion par votre compte Nous', 'Modèles de la communauté Nous Research'],
		usageUrl: 'https://portal.nousresearch.com/manage-subscription'
	},

	// ── Local (sur votre machine) ─────────────────────────────
	lmstudio: {
		desc: 'LM Studio — des modèles sur votre propre machine.',
		about: [
			'Tourne en local : confidentiel et hors ligne',
			'Indiquez l’adresse de votre serveur LM Studio'
		]
	},
	'ollama-local': {
		desc: 'Ollama — un modèle sur votre machine.',
		about: [
			'Tourne chez vous, aucune donnée ne sort',
			'Gratuit et totalement confidentiel'
		]
	},

	// ── Autres ────────────────────────────────────────────────
	'copilot-acp': {
		desc: 'GitHub Copilot (compte de la machine).',
		about: ['Réutilise le login Copilot déjà présent', 'Rien à configurer']
	},
	bedrock: {
		desc: 'AWS Bedrock — l’IA via votre compte Amazon.',
		keyUrl: 'https://console.aws.amazon.com/bedrock',
		about: [
			'Accès à Claude, Llama… depuis AWS',
			'Pour les entreprises déjà sur Amazon Web Services'
		]
	},
	custom: {
		desc: 'Fournisseur personnalisé (compatible OpenAI).',
		about: [
			'Branchez n’importe quelle API compatible OpenAI',
			'Idéal pour un modèle maison ou un serveur privé'
		]
	}
};
