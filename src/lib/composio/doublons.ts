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

export type IntegrationNative = {
	id: string;
	state?: string;
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
