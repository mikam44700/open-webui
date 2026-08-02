/**
 * Logos des fournisseurs — LunarIA V2.
 *
 * On reconnait un logo bien plus vite qu'on ne lit un nom : c'est ce qui fait
 * qu'une grille de trente cartes reste parcourable.
 *
 * Difference avec AgentOS V1 : la-bas, le bridge renvoyait lui-meme le nom du
 * fichier de logo pour chaque fournisseur. Ici les donnees viennent directement
 * d'Hermes, qui n'en dit rien. On resout donc le logo depuis le nom de
 * l'element — d'ou la table ci-dessous.
 *
 * Regle de correspondance : le nom le PLUS LONG qui apparait dans le texte
 * l'emporte. Sans cela, « openrouter » serait attrape par « openai » (les deux
 * commencent par « open ») et afficherait le mauvais logo.
 */

import { WEBUI_BASE_URL } from '$lib/constants';

/**
 * Mot reconnu dans le nom d'un element -> fichier present dans
 * `static/assets/providers/`. L'extension est portee ici, elle varie.
 */
const TABLE: Record<string, string> = {
	// Les grands noms
	openai: 'openai.png',
	gpt: 'openai.png',
	codex: 'codex.png',
	anthropic: 'claude-color.png',
	claude: 'claude-color.png',
	gemini: 'gemini-color.png',
	'vertex-ai': 'vertex-color.png',
	vertex: 'vertex-color.png',
	google: 'gemini-color.png',
	grok: 'grok.png',
	xai: 'grok.png',
	llama: 'meta-color.svg',
	meta: 'meta-color.svg',
	mistral: 'mistral-color.png',
	cohere: 'cohere-color.png',
	perplexity: 'perplexity-color.png',
	copilot: 'copilot.png',

	// Passerelles multi-modeles
	openrouter: 'openrouter.png',
	huggingface: 'huggingface.png',
	'hugging-face': 'huggingface.png',
	together: 'together-color.png',
	fireworks: 'fireworks-color.png',
	novita: 'novita.png',
	atlascloud: 'atlascloud.svg',
	gmi: 'gmi.png',

	// Hebergeurs et acceleration
	groq: 'groq-color.png',
	cerebras: 'cerebras-color.png',
	nvidia: 'nvidia-color.png',
	bedrock: 'bedrock-color.png',
	aws: 'bedrock-color.png',
	azure: 'azure.png',

	// Modeles chinois
	deepseek: 'deepseek-color.png',
	qwen: 'qwen.png',
	moonshot: 'moonshot.png',
	kimi: 'moonshot.png',
	minimax: 'minimax-color.png',
	stepfun: 'stepfun.png',
	tencent: 'tencent.png',
	baidu: 'baidu-color.png',
	zai: 'zai.png',
	mimo: 'mimo.png',
	xiaomi: 'mimo.png',

	// Local, sur la machine
	ollama: 'ollama.png',
	lmstudio: 'lmstudio.png',
	'lm-studio': 'lmstudio.png',
	vllm: 'vllm.svg',

	// Le moteur et son entourage
	hermes: 'nousresearch.png',
	nous: 'nous-research.png',
	nousresearch: 'nousresearch.png',
	sakana: 'sakana-color.png',
	arcee: 'arcee-color.png',
	opencode: 'opencode.png',
	kilocode: 'kilocode.png',
	atomicchat: 'atomicchat.svg',
	agentos: 'agentos.png'
};

/**
 * Les mots les plus longs d'abord : « openrouter » doit etre teste avant
 * « openai », sinon la sous-chaine courte gagnerait a tort.
 */
const MOTS = Object.keys(TABLE).sort((a, b) => b.length - a.length);

/** Repli quand rien ne correspond : une icone neutre, jamais un carre vide. */
export const LOGO_PAR_DEFAUT = `${WEBUI_BASE_URL}/assets/providers/api.svg`;

export type FamilleLogo = 'modele' | 'messagerie' | 'integration' | 'mcp' | 'web' | 'outil';

const LOGOS_SPECIALISES: Record<Exclude<FamilleLogo, 'modele'>, Record<string, string>> = {
	messagerie: {
		whatsapp: 'messaging/whatsapp.png',
		telegram: 'messaging/telegram.png',
		discord: 'messaging/discord.jpg',
		slack: 'messaging/slack.png',
		signal: 'messaging/signal.png',
		email: 'messaging/email.svg',
		mail: 'messaging/email.svg',
		sms: 'messaging/sms.jpg',
		bluebubbles: 'messaging/imessage.jpg',
		imessage: 'messaging/imessage.jpg'
	},
	integration: {
		'google-workspace': 'integrations/google-workspace.svg',
		google: 'integrations/google-workspace.svg',
		gmail: 'integrations/google/gmail.png',
		calendar: 'integrations/google/calendar.png',
		drive: 'integrations/google/drive.png',
		docs: 'integrations/google/docs.png',
		sheets: 'integrations/google/sheets.png',
		slides: 'integrations/google/slides-icon.png',
		github: 'integrations/github-new.svg',
		notion: 'integrations/notion-new.png',
		obsidian: 'integrations/obsidian-icon.webp',
		microsoft: 'integrations/microsoft/microsoft365.svg',
		outlook: 'integrations/microsoft/outlook.png',
		onedrive: 'integrations/microsoft/onedrive.png',
		slack: 'messaging/slack.png',
		email: 'integrations/email-new.png',
		airtable: 'integrations/airtable-new.png',
		box: 'integrations/box/box-logo.png',
		dropbox: 'integrations/dropbox/dropbox-logo.png',
		calendly: 'integrations/calendly/calendly-logo.png',
		clickup: 'integrations/clickup/clickup-logo.jpg',
		salesforce: 'integrations/salesforce/salesforce-logo.svg'
	},
	mcp: {
		'google-calendar': 'connectors/google-calendar.svg',
		'google-drive': 'connectors/google-drive.svg',
		'data-gouv': 'connectors/data-gouv-fr.svg',
		gmail: 'connectors/gmail.png',
		github: 'connectors/github.svg',
		notion: 'connectors/notion.svg',
		slack: 'connectors/slack.svg',
		stripe: 'connectors/stripe.png',
		hubspot: 'connectors/hubspot.svg',
		figma: 'connectors/figma.svg',
		airtable: 'connectors/airtable.svg',
		asana: 'connectors/asana.svg',
		atlassian: 'connectors/atlassian.svg',
		canva: 'connectors/canva.png',
		context7: 'connectors/context7.png',
		'apify': 'connectors/apify.webp',
		crawl4ai: 'connectors/crawl4ai.svg',
		postgres: 'connectors/postgres.png',
		sqlite: 'connectors/sqlite.png',
		filesystem: 'connectors/filesystem.png',
		redis: 'connectors/redis.png',
		n8n: 'connectors/n8n.svg',
		mcp: 'connectors/mcp.svg'
	},
	web: {
		duckduckgo: 'web-providers/duckduckgo.png',
		ddgs: 'web-providers/duckduckgo.png',
		brave: 'web-providers/brave.webp',
		exa: 'web-providers/exa.jpeg',
		firecrawl: 'web-providers/firecrawl.png',
		tavily: 'web-providers/tavily.png',
		searxng: 'web-providers/searxng.png',
		serpapi: 'web-providers/serpapi.png',
		serper: 'web-providers/serper.png',
		jina: 'web-providers/jina.png',
		linkup: 'web-providers/linkup.png',
		parallel: 'web-providers/parallel.svg',
		perplexity: 'web-providers/perplexity.png',
		chromium: 'web-providers/chromium.png',
		browserbase: 'web-providers/browserbase.png',
		'browser-use': 'web-providers/browser-use.png',
		camofox: 'web-providers/camofox.png',
		xai: 'web-providers/xai.png'
	},
	outil: {
		browser: 'web-providers/chromium.png',
		web: 'web-providers/duckduckgo.png',
		search: 'web-providers/duckduckgo.png',
		github: 'connectors/github.svg',
		memory: 'connectors/memory.jpg',
		filesystem: 'connectors/filesystem.png',
		terminal: 'connectors/git.png',
		image: 'web-providers/fal.jpg',
		video: 'connectors/davinci-resolve.png',
		audio: 'connectors/elevenlabs.png',
		tts: 'connectors/elevenlabs.png',
		homeassistant: 'web-providers/homeassistant.png',
		spotify: 'web-providers/spotify.png'
	}
};

const fichierSpecialise = (
	famille: Exclude<FamilleLogo, 'modele'>,
	...textes: (string | undefined)[]
): string | null => {
	const texte = textes.filter(Boolean).join(' ').toLowerCase();
	const table = LOGOS_SPECIALISES[famille];
	const mot = Object.keys(table)
		.sort((a, b) => b.length - a.length)
		.find((candidat) => texte.includes(candidat));
	return mot ? table[mot] : null;
};

/** Logo de la bonne famille, avec repli sur le catalogue des modèles. */
export const urlLogoCapacite = (
	famille: FamilleLogo,
	...textes: (string | undefined)[]
): string | null => {
	if (famille === 'modele') return urlLogo(...textes);
	const fichier = fichierSpecialise(famille, ...textes);
	return fichier ? `${WEBUI_BASE_URL}/assets/${fichier}` : urlLogo(...textes);
};

/**
 * Logos dont le fond fait partie de l'image — carre plein de couleur. Ils
 * s'affichent bord a bord ; les autres sont des icones sur fond transparent et
 * gardent une petite marge. Sans cette distinction, un carre noir se retrouve
 * cerne d'un liere blanc disgracieux.
 */
const FOND_PLEIN = new Set([
	'mimo.png',
	'nvidia-color.png',
	'zai.png',
	'gmi.png',
	'lmstudio.png',
	'moonshot.png',
	'nous-research.png',
	'groq-color.png',
	'perplexity-color.png'
]);

/** Fichier de logo correspondant a un nom, ou null si rien ne correspond. */
const fichierPour = (...textes: (string | undefined)[]): string | null => {
	const texte = textes.filter(Boolean).join(' ').toLowerCase();
	if (!texte) return null;
	const trouve = MOTS.find((mot) => texte.includes(mot));
	return trouve ? TABLE[trouve] : null;
};

/** Adresse du logo, ou null quand aucun ne correspond. */
export const urlLogo = (...textes: (string | undefined)[]): string | null => {
	const fichier = fichierPour(...textes);
	return fichier ? `${WEBUI_BASE_URL}/assets/providers/${fichier}` : null;
};

/** Vrai si le logo doit remplir son carre au lieu de garder une marge. */
export const logoBordABord = (...textes: (string | undefined)[]): boolean => {
	const fichier = fichierPour(...textes);
	return fichier ? FOND_PLEIN.has(fichier) : false;
};

/**
 * Initiales de repli, quand aucun logo ne correspond. Deux lettres au plus :
 * au-dela, la pastille devient illisible a 40 pixels.
 */
export const initiales = (titre: string): string =>
	titre
		.split(/[\s_\-.]+/)
		.filter(Boolean)
		.slice(0, 2)
		.map((mot) => mot[0]?.toUpperCase() ?? '')
		.join('');
