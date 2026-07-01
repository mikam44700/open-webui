// Infos « client » des fournisseurs de modèles IA (page Modèles IA) : phrase grise courte,
// déroulant « Voir ce que ça fait », et lien « Obtenir la clé » (page officielle où récupérer
// sa clé API). Clé = identifiant Hermes du fournisseur (source : bridge hermes_adapter).
// Un id absent retombe proprement (pas de desc dédiée, pas de lien).

export type ProviderInfo = {
	desc?: string;
	about?: string[];
	keyUrl?: string;
};

export const PROVIDER_INFO: Record<string, ProviderInfo> = {
	'openai-api': {
		desc: 'Les modèles GPT d’OpenAI (par clé).',
		keyUrl: 'https://platform.openai.com/api-keys',
		about: ['Modèles GPT : raisonnement, rédaction, code', 'Qualité premium', 'Facturation à l’usage']
	},
	'openai-codex': {
		desc: 'GPT-5.5 via votre compte OpenAI Codex.',
		about: ['Réutilise votre abonnement ChatGPT / Codex', 'Aucune clé à saisir']
	},
	anthropic: {
		desc: 'Les modèles Claude d’Anthropic.',
		keyUrl: 'https://console.anthropic.com/settings/keys',
		about: ['Modèles Claude : analyse, rédaction longue, code', 'Qualité premium', 'Facturation à l’usage']
	},
	gemini: {
		desc: 'Les modèles Gemini de Google.',
		keyUrl: 'https://aistudio.google.com/app/apikey',
		about: ['Modèles Gemini rapides et multimodaux', 'Bon rapport qualité / prix']
	},
	google: {
		desc: 'Google AI Studio (modèles Gemini).',
		keyUrl: 'https://aistudio.google.com/app/apikey',
		about: ['Accès aux modèles Gemini', 'Offre gratuite pour démarrer']
	},
	mistral: {
		desc: 'Les modèles de Mistral AI.',
		keyUrl: 'https://console.mistral.ai/api-keys',
		about: ['Modèles européens', 'Bon rapport qualité / prix']
	},
	openrouter: {
		desc: 'Des centaines de modèles avec une seule clé.',
		keyUrl: 'https://openrouter.ai/keys',
		about: ['Une clé pour de nombreux modèles', 'Idéal pour comparer et économiser']
	},
	groq: {
		desc: 'Inférence ultra-rapide (Groq).',
		keyUrl: 'https://console.groq.com/keys',
		about: ['Réponses très rapides', 'Bon marché']
	},
	deepseek: {
		desc: 'Modèles DeepSeek, économiques et doués en code.',
		keyUrl: 'https://platform.deepseek.com/api_keys',
		about: ['Très économique', 'Bon en raisonnement et en code']
	},
	xai: {
		desc: 'Les modèles Grok de xAI (par clé).',
		keyUrl: 'https://console.x.ai',
		about: ['Modèles Grok', 'Recherche web en temps réel']
	},
	'xai-oauth': {
		desc: 'Grok via votre compte X (SuperGrok / Premium+).',
		about: ['Réutilise votre abonnement X', 'Aucune clé à saisir']
	},
	zai: {
		desc: 'Les modèles GLM de Z.AI.',
		keyUrl: 'https://z.ai/manage-apikey/apikey-list',
		about: ['Modèles GLM', 'Bon rapport qualité / prix']
	},
	'kimi-coding': {
		desc: 'Kimi (Moonshot), plan codage.',
		keyUrl: 'https://platform.moonshot.ai/console/api-keys',
		about: ['Modèles Kimi', 'Grande fenêtre de contexte']
	},
	'kimi-coding-cn': {
		desc: 'Kimi (Moonshot), endpoint Chine.',
		keyUrl: 'https://platform.moonshot.cn/console/api-keys',
		about: ['Modèles Kimi (Chine)']
	},
	minimax: {
		desc: 'Les modèles MiniMax.',
		keyUrl: 'https://www.minimax.io/platform',
		about: ['Texte et audio', 'Économique']
	},
	'minimax-cn': {
		desc: 'MiniMax, endpoint Chine.',
		keyUrl: 'https://platform.minimaxi.com',
		about: ['Modèles MiniMax (Chine)']
	},
	'minimax-oauth': {
		desc: 'MiniMax via votre compte.',
		about: ['Connexion par compte', 'Aucune clé à saisir']
	},
	alibaba: {
		desc: 'Qwen Cloud (Alibaba).',
		keyUrl: 'https://bailian.console.alibabacloud.com',
		about: ['Modèles Qwen', 'Large gamme de tailles']
	},
	'alibaba-coding-plan': {
		desc: 'Alibaba, plan codage (Qwen).',
		about: ['Modèles Qwen orientés code']
	},
	'qwen-oauth': {
		desc: 'Qwen via votre compte (Portal).',
		about: ['Connexion par compte', 'Aucune clé à saisir']
	},
	xiaomi: {
		desc: 'Les modèles MiMo de Xiaomi.',
		about: ['Modèles MiMo']
	},
	nvidia: {
		desc: 'NVIDIA NIM (modèles hébergés).',
		keyUrl: 'https://build.nvidia.com',
		about: ['Modèles hébergés par NVIDIA']
	},
	huggingface: {
		desc: 'Hugging Face (modèles open source).',
		keyUrl: 'https://huggingface.co/settings/tokens',
		about: ['Accès à de nombreux modèles open source']
	},
	'ollama-cloud': {
		desc: 'Ollama Cloud (modèles hébergés).',
		keyUrl: 'https://ollama.com/settings/keys',
		about: ['Modèles Ollama dans le cloud']
	},
	lmstudio: {
		desc: 'LM Studio (modèles sur votre machine).',
		about: ['Tourne en local', 'Confidentiel, hors ligne', 'Indiquez l’adresse du serveur local']
	},
	'ollama-local': {
		desc: 'Modèle local via Ollama.',
		about: ['Tourne sur votre machine', 'Confidentiel : aucune donnée ne sort']
	},
	'opencode-zen': {
		desc: 'OpenCode Zen (passerelle de modèles).',
		about: ['Accès à de nombreux modèles']
	},
	'opencode-go': {
		desc: 'OpenCode Go (passerelle de modèles).',
		about: ['Accès à de nombreux modèles']
	},
	novita: {
		desc: 'NovitaAI (modèles hébergés).',
		keyUrl: 'https://novita.ai/settings/key-management',
		about: ['Modèles hébergés', 'Économique']
	},
	'tencent-tokenhub': {
		desc: 'Tencent TokenHub.',
		about: ['Modèles hébergés par Tencent']
	},
	copilot: {
		desc: 'GitHub Copilot (par clé).',
		keyUrl: 'https://github.com/settings/tokens',
		about: ['Modèles via GitHub Copilot']
	},
	'copilot-acp': {
		desc: 'GitHub Copilot (compte de la machine).',
		about: ['Réutilise le login Copilot de la machine', 'Rien à configurer']
	},
	stepfun: {
		desc: 'StepFun (Step Plan).',
		about: ['Modèles StepFun']
	},
	arcee: {
		desc: 'Arcee AI.',
		keyUrl: 'https://models.arcee.ai',
		about: ['Modèles Arcee']
	},
	gmi: {
		desc: 'GMI Cloud (modèles hébergés).',
		about: ['Modèles hébergés par GMI']
	},
	kilocode: {
		desc: 'Kilo Code (passerelle de modèles).',
		keyUrl: 'https://app.kilocode.ai',
		about: ['Plusieurs modèles pour le code']
	},
	'azure-foundry': {
		desc: 'Azure AI Foundry (Microsoft).',
		keyUrl: 'https://ai.azure.com',
		about: ['Modèles hébergés sur Azure']
	},
	bedrock: {
		desc: 'AWS Bedrock (modèles via votre compte AWS).',
		keyUrl: 'https://console.aws.amazon.com/bedrock',
		about: ['Accès aux modèles via AWS', 'Identifiants AWS requis']
	},
	nous: {
		desc: 'Nous Portal (modèles Nous Research).',
		about: ['Connexion par compte', 'Modèles Nous Research']
	},
	custom: {
		desc: 'Fournisseur personnalisé (compatible OpenAI).',
		about: ['Branchez n’importe quelle API compatible OpenAI']
	}
};
