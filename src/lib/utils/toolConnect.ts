// Types, logos et statuts des fournisseurs d'un toolset (recherche web, navigateur, X…).
// Source de vérité UNIQUE, partagée par le pop-up « Connecter » (Outils) et la page
// « Recherche & web ». Évite toute duplication (DRY).

// Logos des fournisseurs (mappés par `slug` renvoyé par le bridge).
import duckduckgoLogo from '$lib/assets/web-providers/duckduckgo.png';
import exaLogo from '$lib/assets/web-providers/exa.jpeg';
import firecrawlLogo from '$lib/assets/web-providers/firecrawl.png';
// Réutilise le logo Brave « propre » du catalogue MCP (fond net) plutôt que le .webp
// de web-providers qui rendait mal (transparence visible) sur la page Recherche & web.
import braveLogo from '$lib/assets/connectors/brave-search.png';
import tavilyLogo from '$lib/assets/web-providers/tavily.png';
import parallelLogo from '$lib/assets/web-providers/parallel.svg';
import searxngLogo from '$lib/assets/web-providers/searxng.png';
import xaiLogo from '$lib/assets/web-providers/xai.png';
import nousLogo from '$lib/assets/providers/nousresearch.png';
import chromiumLogo from '$lib/assets/web-providers/chromium.png';
import camofoxLogo from '$lib/assets/web-providers/camofox.png';
import browserUseLogo from '$lib/assets/web-providers/browser-use.png';
import browserbaseLogo from '$lib/assets/web-providers/browserbase.png';
import cuaLogo from '$lib/assets/web-providers/cua.png';
import openrouterLogo from '$lib/assets/providers/openrouter.svg';
import falLogo from '$lib/assets/web-providers/fal.jpg';
import kreaLogo from '$lib/assets/web-providers/krea.png';
import openaiLogo from '$lib/assets/providers/openai.svg';
import codexLogo from '$lib/assets/providers/codex.png';
import grokLogo from '$lib/assets/providers/grok.svg';
import edgeLogo from '$lib/assets/web-providers/edge.jpg';
import elevenlabsLogo from '$lib/assets/web-providers/elevenlabs.png';
import kittenLogo from '$lib/assets/web-providers/kitten.webp';
import piperLogo from '$lib/assets/web-providers/piper.svg';
import mistralLogo from '$lib/assets/providers/mistral-color.svg';
import geminiLogo from '$lib/assets/providers/gemini-color.svg';
import homeassistantLogo from '$lib/assets/web-providers/homeassistant.png';
import spotifyLogo from '$lib/assets/web-providers/spotify.png';
import linkupLogo from '$lib/assets/web-providers/linkup.png';
import serperLogo from '$lib/assets/web-providers/serper.png';
import serpapiLogo from '$lib/assets/web-providers/serpapi.png';
import perplexityLogo from '$lib/assets/web-providers/perplexity.png';
import jinaLogo from '$lib/assets/web-providers/jina.png';

export type Field = {
	key: string;
	label: string;
	default: string | null;
	url: string | null;
	secret: boolean;
	present: boolean;
};

export type Provider = {
	name: string;
	tag: string | null;
	badge: string | null;
	kind: string;
	fields: Field[];
	slug?: string | null;
	advanced?: boolean;
	category?: string | null;
	connected?: boolean | null;
};

export type ProviderState =
	| 'saved'
	| 'detected'
	| 'disconnected'
	| 'active'
	| 'local'
	| 'subscription'
	| 'none';

export const LOGO_BY_SLUG: Record<string, string> = {
	duckduckgo: duckduckgoLogo,
	exa: exaLogo,
	firecrawl: firecrawlLogo,
	brave: braveLogo,
	tavily: tavilyLogo,
	parallel: parallelLogo,
	searxng: searxngLogo,
	xai: xaiLogo,
	nous: nousLogo,
	chromium: chromiumLogo,
	camofox: camofoxLogo,
	'browser-use': browserUseLogo,
	browserbase: browserbaseLogo,
	cua: cuaLogo,
	openrouter: openrouterLogo,
	fal: falLogo,
	krea: kreaLogo,
	openai: openaiLogo,
	codex: codexLogo,
	grok: grokLogo,
	edge: edgeLogo,
	elevenlabs: elevenlabsLogo,
	kitten: kittenLogo,
	piper: piperLogo,
	mistral: mistralLogo,
	gemini: geminiLogo,
	homeassistant: homeassistantLogo,
	spotify: spotifyLogo,
	linkup: linkupLogo,
	serper: serperLogo,
	serpapi: serpapiLogo,
	perplexity: perplexityLogo,
	jina: jinaLogo
};

// Logos au tracé sombre/transparent : illisibles sur fond sombre → fond blanc.
export const WHITE_BG_SLUGS = new Set([
	'brave',
	'tavily',
	'parallel',
	'xai',
	'camofox',
	'chromium',
	'openrouter',
	'krea',
	'openai',
	'grok',
	'piper',
	'elevenlabs',
	'mistral',
	'gemini',
	'jina'
]);

// Logos « larges et courts » (ex. Mistral : bandes horizontales) qui paraissent minuscules
// avec la marge standard : on les colle aux bords du carré (sans padding) pour les agrandir.
export const LOGO_TIGHT_SLUGS = new Set(['mistral']);

// Fournisseurs locaux (modèle téléchargé à la 1re utilisation) : pas de clé, mais pas
// « actif » d'office non plus → libellé neutre « Sans clé · local ».
export const LOCAL_SLUGS = new Set(['kitten', 'piper']);

// Fournisseurs « gérés » qui dépendent d'un abonnement payant (pas actifs d'office).
export const SUBSCRIPTION_SLUGS = new Set(['nous']);

// Regroupement des fournisseurs avancés par catégorie, dans cet ordre.
export const CATEGORY_ORDER = ['free', 'self_hosted', 'paid'];
export const CATEGORY_LABEL: Record<string, string> = {
	free: 'Gratuit',
	self_hosted: 'Auto-hébergé · serveur à lancer',
	paid: 'Payant'
};

// « Ce que ça fait » par fournisseur (slug) : puces affichées dans le déroulant des cartes.
// Les fournisseurs sans entrée retombent sur leur description courte (tag) → le lien
// « Voir ce que ça fait » apparaît partout.
export const PROVIDER_ABOUT: Record<string, string[]> = {
	duckduckgo: [
		'Recherche web gratuite, sans clé ni inscription',
		'Trouve rapidement des pages pertinentes',
		'Ne lit pas le contenu détaillé des pages (à coupler à un lecteur)'
	],
	exa: [
		'Recherche sémantique : comprend le sens de la demande, pas juste les mots-clés',
		'Récupère directement le contenu des pages',
		'Idéale pour la veille et la recherche documentaire'
	],
	firecrawl: [
		'Recherche ET lit des pages web entières',
		'Renvoie un texte propre, prêt pour l’IA',
		'Parfait pour extraire le contenu d’un site'
	],
	brave: [
		'Moteur de recherche indépendant, respectueux de la vie privée',
		'Offre gratuite : 2 000 recherches par mois',
		'Recherche seule (ne lit pas le contenu des pages)'
	],
	tavily: [
		'Recherche et lecture de pages réunies en un seul service',
		'Pensé pour l’IA : simple et efficace',
		'Nécessite une clé API'
	],
	searxng: [
		'Méta-moteur privé que vous hébergez vous-même',
		'Interroge plusieurs moteurs à la fois, sans pister',
		'Nécessite l’adresse de votre instance SearXNG'
	],
	parallel: [
		'Recherche optimisée par objectif',
		'Lit plusieurs pages en parallèle pour des réponses plus complètes',
		'Utile pour les recherches approfondies'
	],
	xai: [
		'Recherche web en temps réel propulsée par Grok (xAI)',
		'Réutilise votre clé xAI si déjà connectée à Grok'
	],
	nous: [
		'Recherche gérée, incluse dans l’abonnement Nous',
		'Aucune clé à saisir, rien à configurer'
	],
	chromium: [
		'Navigateur Chromium intégré, tourne sur votre machine',
		'Navigue, clique, remplit et fait défiler les pages',
		'Gratuit, privé, aucune clé à saisir'
	],
	camofox: [
		'Navigateur anti-détection (basé sur Firefox)',
		'Utile pour les sites qui bloquent les robots',
		'À héberger soi-même (indiquer l’adresse)'
	],
	'browser-use': [
		'Navigateur dans le cloud, exécuté à distance',
		'Automatise la navigation à grande échelle',
		'Nécessite une clé API'
	],
	browserbase: [
		'Navigateur cloud avec mode furtif et proxies intégrés',
		'Contourne les blocages, navigue de façon anonyme',
		'Nécessite une clé API et un identifiant de projet'
	],
	linkup: [
		'Recherche web souveraine (société française)',
		'Réputée pour la fiabilité de ses réponses ; lit les pages',
		'Offre gratuite généreuse (clé gratuite requise)'
	],
	serper: [
		'Accès direct aux résultats de Google, rapide et bon marché',
		'Idéal quand vous voulez exactement ce que renvoie Google',
		'Crédits gratuits à l’inscription ; recherche seule'
	],
	jina: [
		'Recherche web ET lecture de pages en texte propre',
		'Fonctionne gratuitement sans clé (quota modeste)',
		'Une clé gratuite augmente les quotas'
	],
	serpapi: [
		'Résultats structurés de plus de 40 moteurs (Google par défaut)',
		'Fiable et complet, pour de la recherche exigeante',
		'100 recherches gratuites par mois, puis payant'
	],
	perplexity: [
		'Moteur de réponse en temps réel qui cite ses sources',
		'Pratique pour les questions d’actualité, liens à l’appui',
		'Nécessite une clé API'
	]
};

// Phrase COURTE affichée en gris sous le nom (jamais coupée). Le détail va dans le
// déroulant « Voir ce que ça fait » (PROVIDER_ABOUT).
export const PROVIDER_SHORT: Record<string, string> = {
	duckduckgo: 'Recherche web gratuite, sans clé.',
	exa: 'Recherche intelligente qui lit les pages.',
	firecrawl: 'Recherche et lit des pages entières.',
	brave: 'Moteur de recherche privé et gratuit.',
	tavily: 'Recherche + lecture de pages pour l’IA.',
	searxng: 'Méta-moteur privé, auto-hébergé.',
	parallel: 'Recherche approfondie sur plusieurs pages.',
	xai: 'Recherche web en temps réel (Grok).',
	nous: 'Incluse dans l’abonnement Nous.',
	chromium: 'Navigateur local, gratuit et privé.',
	camofox: 'Navigateur anti-détection, auto-hébergé.',
	'browser-use': 'Navigateur cloud, piloté à distance.',
	browserbase: 'Navigateur cloud furtif avec proxies.',
	fal: 'Nombreux modèles d’images et de vidéo.',
	krea: 'Génération d’images guidée par référence.',
	mistral: 'Synthèse vocale multilingue (Voxtral).',
	linkup: 'Recherche souveraine française, fiable.',
	serper: 'Résultats Google, rapides et bon marché.',
	serpapi: 'Résultats de 40+ moteurs de recherche.',
	perplexity: 'Réponses en temps réel, sources citées.',
	jina: 'Recherche + lecture de pages, gratuit.'
};

// État affiché par fournisseur. On n'affirme QUE ce qu'on sait avec certitude :
// - saved       : kind=key avec toutes ses clés saisies (saisie ≠ clé valide)
// - detected    : géré via compte/OAuth et réellement connecté
// - disconnected: géré via compte/OAuth mais PAS connecté → action requise ailleurs
// - active      : service en ligne sans clé, marche tout de suite
// - local       : tourne en local sans clé, modèle téléchargé à la 1re utilisation
// - subscription: géré, nécessite un abonnement Nous actif
export const providerStatus = (p: Provider): ProviderState => {
	if (p.kind === 'managed') {
		if (p.slug && SUBSCRIPTION_SLUGS.has(p.slug)) return 'subscription';
		if (p.slug && LOCAL_SLUGS.has(p.slug)) return 'local';
		if (p.connected === true) return 'detected';
		if (p.connected === false) return 'disconnected';
		return 'active';
	}
	if (p.kind === 'key' && p.fields.length > 0 && p.fields.every((f) => f.present)) return 'saved';
	return 'none';
};
