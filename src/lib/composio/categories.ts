/**
 * Classement metier des applications Composio.
 *
 * Composio en propose plus de mille, rangees par ordre alphabetique. Presentees
 * telles quelles, elles commencent par « 1password, 21risk, 2chat, Ably » : un
 * dirigeant n'y trouve jamais sa messagerie. On garde donc la meme approche que
 * pour les fournisseurs de modeles (lib/catalog/provider-taxonomy.ts) : un
 * classement maison, en francais, oriente usage.
 *
 * Cette liste est celle de Mike, arretee le 2 aout 2026 : les applications les
 * plus repandues en entreprise, rangees par usage, avec un espace dedie a
 * Google et un a Microsoft — un client qui travaille sur l'un des deux veut
 * tout brancher d'un coup. Tout ce qui n'y figure pas reste atteignable par la
 * recherche et par le reste du catalogue : rien n'est cache, seulement range
 * derriere ce qui sert tous les jours. Ne pas y toucher sans le lui demander.
 *
 * Les identifiants ont ete verifies un par un contre le catalogue public de
 * Composio. Un identifiant invente donnerait une categorie vide sans que la
 * cause soit visible.
 */

export type Categorie = {
	id: string;
	libelle: string;
	applications: string[];
};

export const CATEGORIES: Categorie[] = [
	{
		id: 'google',
		libelle: 'Espace Google',
		// `google_chat`, ce sont les Espaces de Google Chat. Tout l'univers Google
		// est reuni ici plutot qu'eparpille : un client qui travaille sur Google
		// veut tout brancher d'un coup, pas chercher Gmail dans un menu et Drive
		// dans un autre.
		applications: [
			'gmail',
			'googlecalendar',
			'googledrive',
			'googledocs',
			'googlesheets',
			'googleslides',
			'googlemeet',
			'google_chat',
			'googletasks',
			'googleforms',
			'googlecontacts'
		]
	},
	{
		id: 'microsoft',
		libelle: 'Espace Microsoft',
		// Meme logique, cote Microsoft. SharePoint n'existe pas chez Composio :
		// verifie, absent. Ne pas l'ajouter en esperant qu'il apparaisse.
		applications: ['outlook', 'one_drive', 'microsoft_teams']
	},
	{
		id: 'discussion',
		libelle: 'Discussion & réunions',
		applications: ['slack', 'zoom', 'whatsapp']
	},
	{
		id: 'rendezvous',
		libelle: 'Rendez-vous',
		applications: ['calendly', 'cal']
	},
	{
		id: 'fichiers',
		libelle: 'Fichiers',
		applications: ['dropbox', 'box']
	},
	{
		id: 'clients',
		libelle: 'Clients & ventes',
		applications: ['hubspot', 'salesforce', 'pipedrive', 'zoho']
	},
	{
		id: 'projets',
		libelle: 'Projets & tâches',
		applications: [
			'notion',
			'airtable',
			'trello',
			'asana',
			'monday',
			'clickup',
			'jira',
			'confluence'
		]
	},
	{
		id: 'support',
		libelle: 'Support client',
		applications: ['zendesk', 'intercom', 'freshdesk']
	},
	{
		id: 'compta',
		libelle: 'Compta & paiement',
		// Aucun outil francais chez Composio : Sage, Pennylane et Qonto sont
		// absents, verifie. La compta d'une PME francaise ne se branche pas ici.
		applications: ['stripe', 'paypal', 'quickbooks', 'xero']
	},
	{
		id: 'marketing',
		libelle: 'Marketing & e-mailing',
		applications: ['mailchimp', 'brevo', 'typeform', 'googleads']
	},
	{
		id: 'vente-en-ligne',
		libelle: 'Vente en ligne & automatisation',
		// WooCommerce et Zapier sont absents de Composio, verifie.
		applications: ['shopify', 'make']
	},
	{
		id: 'rh',
		libelle: 'RH & services internes',
		applications: ['bamboohr', 'servicenow']
	},
	{
		id: 'signature',
		libelle: 'Signature électronique',
		applications: ['docusign', 'dropbox_sign']
	},
	{
		id: 'reseaux',
		libelle: 'Réseaux sociaux',
		applications: ['linkedin', 'facebook', 'twitter', 'instagram', 'tiktok', 'youtube']
	},
	{
		id: 'developpement',
		libelle: 'Développement',
		// figma et linear existent chez Composio mais le moteur porte deja ses
		// propres serveurs MCP pour eux : les remettre ici recreerait un doublon.
		applications: ['github', 'gitlab']
	}
];

/** Identifiant -> categorie, construit une fois. */
export const CATEGORIE_PAR_APPLICATION = new Map<string, Categorie>(
	CATEGORIES.flatMap((categorie) =>
		categorie.applications.map((slug) => [slug, categorie] as const)
	)
);

/**
 * Noms rendus lisibles en francais.
 *
 * Composio renvoie deja des noms corrects ; on ne surcharge que la ou son
 * libelle prete a confusion sur une carte etroite, ou n'est pas francais.
 */
export const NOMS_FR: Record<string, string> = {
	googlecalendar: 'Agenda Google',
	googledrive: 'Google Drive',
	googledocs: 'Google Docs',
	googlesheets: 'Google Sheets',
	googlemeet: 'Google Meet',
	one_drive: 'OneDrive',
	microsoft_teams: 'Microsoft Teams',
	twitter: 'X (ex-Twitter)',
	cal: 'Cal.com',
	dropbox_sign: 'Dropbox Sign',
	googleslides: 'Google Slides',
	google_chat: 'Google Chat (Espaces)',
	googletasks: 'Google Tasks',
	googleforms: 'Google Forms',
	googlecontacts: 'Contacts Google',
	googleads: 'Google Ads',
	zoho: 'Zoho CRM',
	monday: 'Monday.com'
};

export const nomAffiche = (slug: string, nomComposio: string): string =>
	NOMS_FR[slug] ?? nomComposio;
