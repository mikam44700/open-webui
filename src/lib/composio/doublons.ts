/**
 * Une application, une seule carte.
 *
 * Depuis l'arrivee de Composio, l'onglet Integrations porte deux couches qui se
 * recouvrent : les integrations natives du moteur, et le catalogue Composio.
 * Le client voyait Gmail deux fois — une fois par Composio, qui marche, et une
 * fois par la carte native « Google Workspace », dont le bouton ne fait rien
 * (dix fonctions de lib/apis/integrations renvoient `unavailable`).
 *
 * Arbitrage, decide par Mike le 2 aout 2026, sans exception :
 *
 *   - des que Composio est actif, toute carte native qu'il recouvre disparait,
 *     connectee ou non ;
 *   - ce que Composio ne couvre pas reste natif (coffre local, protocole de
 *     messagerie, domotique).
 *
 * Consequence assumee : une integration native encore branchee continue de
 * fonctionner cote moteur sans carte a l'ecran. Elle se retire alors depuis les
 * outils du moteur, plus depuis cet onglet.
 */

/** Identifiant natif -> identifiants Composio qui rendent le meme service. */
export const COUVERTURE_COMPOSIO: Record<string, string[]> = {
	'google-workspace': [
		'gmail',
		'googledrive',
		'googlecalendar',
		'googledocs',
		'googlesheets',
		'googlemeet'
	],
	'microsoft-365': ['outlook', 'one_drive', 'microsoft_teams'],
	notion: ['notion'],
	github: ['github'],
	airtable: ['airtable'],
	x: ['twitter'],
	linkedin: ['linkedin'],
	tiktok: ['tiktok'],
	facebook: ['facebook'],
	instagram: ['instagram'],
	calendly: ['calendly'],
	'cal-com': ['cal'],
	box: ['box'],
	dropbox: ['dropbox'],
	salesforce: ['salesforce'],
	clickup: ['clickup']
	// Absents volontairement : obsidian (coffre sur le disque), email (IMAP/SMTP,
	// un protocole), apple, hue (domotique locale). Composio ne les atteint pas.
};

/**
 * Meme probleme, deuxieme couche : le catalogue MCP.
 *
 * Vingt-quatre des cinquante-sept entrees MCP rendent un service que Composio
 * rend deja — et six des sept vedettes de la page. Le client connectait Gmail
 * par Composio, passait sur l'onglet MCP, et Gmail y trononait toujours en
 * vedette comme s'il n'etait pas branche. Notion, GitHub et Airtable
 * apparaissaient meme trois fois : natif, Composio et MCP.
 *
 * Arbitrage, decide par Mike le 3 aout 2026, puis DURCI le meme jour :
 *
 *   - premiere version : l'entree quittait la vitrine mais restait dans
 *     « Tout parcourir ». Mike a tranche que non — un doublon range plus
 *     loin reste un doublon ;
 *   - version en vigueur : Composio actif, l'entree disparait de TOUT
 *     l'onglet MCP, vitrine et catalogue compris ;
 *   - un connecteur deja installe reste toujours a l'ecran : on ne cache
 *     jamais ce qui tourne. Il s'affiche depuis `connectors`, pas d'ici ;
 *   - Composio muet, rien n'est filtre : mieux vaut un doublon qu'un onglet
 *     vide parce qu'une source tierce n'a pas repondu (regle D27).
 *
 * Meme regle que pour les natives, donc : une application, un seul endroit
 * ou la brancher. Cout assume : le serveur MCP officiel de Figma (Code
 * Connect, ecriture sur le canvas) et celui de Linear sortent de l'ecran
 * alors que le connecteur Composio ne rend pas exactement le meme service.
 * Ils restent installables cote moteur.
 */
export const COUVERTURE_MCP: Record<string, string[]> = {
	gmail: ['gmail'],
	'google-calendar': ['googlecalendar'],
	'google-drive': ['googledrive'],
	notion: ['notion'],
	slack: ['slack'],
	asana: ['asana'],
	linear: ['linear'],
	airtable: ['airtable'],
	youtube: ['youtube'],
	atlassian: ['jira', 'confluence'],
	hubspot: ['hubspot'],
	stripe: ['stripe'],
	paypal: ['paypal'],
	quickbooks: ['quickbooks'],
	figma: ['figma'],
	elevenlabs: ['elevenlabs'],
	github: ['github'],
	'docker-hub': ['docker_hub'],
	cloudflare: ['cloudflare'],
	vercel: ['vercel'],
	sentry: ['sentry'],
	supabase: ['supabase'],
	neon: ['neon'],
	mistral: ['mistral_ai']
	// Absents volontairement : data-gouv-fr, brave-search, canva, plaid, blender,
	// postgres, kubernetes, filesystem, memory, les entrees crypto — Composio ne
	// les porte pas, ce sont eux qui justifient l'onglet.
};

export type IntegrationNative = {
	id: string;
	state?: string;
};

/** Entree du catalogue MCP, reduite a ce dont le tri a besoin. */
export type EntreeMcp = {
	name: string;
};

/** Composio rend-il deja ce service ? */
export const couvertParComposio = (id: string): boolean =>
	(COUVERTURE_COMPOSIO[id]?.length ?? 0) > 0;

/**
 * Ne garde que ce que Composio ne sait pas faire.
 *
 * Sans Composio actif, la liste est rendue telle quelle : une installation sans
 * cle ne perd rien.
 */
export const filtrerNatives = <T extends IntegrationNative>(
	integrations: T[],
	composioActif: boolean
): T[] => {
	if (!composioActif) return integrations;
	return integrations.filter((integration) => !couvertParComposio(integration.id));
};

/** Composio rend-il deja ce que ce serveur MCP rendrait ? */
export const couvertParComposioEnMcp = (name: string): boolean =>
	(COUVERTURE_MCP[`${name}`.toLowerCase()]?.length ?? 0) > 0;

/**
 * Ne garde dans l'onglet MCP que ce que Composio ne sait pas faire.
 *
 * A appliquer au catalogue ENTIER — vitrine et « Tout parcourir » — jamais aux
 * connecteurs installes, qui restent affiches en toutes circonstances.
 */
export const filtrerDoublonsMcp = <T extends EntreeMcp>(
	entrees: T[],
	composioActif: boolean
): T[] => {
	if (!composioActif) return entrees;
	return entrees.filter((entree) => !couvertParComposioEnMcp(entree.name));
};
