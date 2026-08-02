/**
 * Classement metier des applications Composio.
 *
 * Composio en propose plus de mille, rangees par ordre alphabetique. Presentees
 * telles quelles, elles commencent par « 1password, 21risk, 2chat, Ably » : un
 * dirigeant n'y trouve jamais sa messagerie. On garde donc la meme approche que
 * pour les fournisseurs de modeles (lib/catalog/provider-taxonomy.ts) : un
 * classement maison, en francais, oriente usage.
 *
 * Cette vitrine est celle de Mike, arretee application par application le
 * 2 aout 2026 : vingt et une applications, sept sections. Elle est COURTE
 * volontairement — cinquante-huit cartes deroulees noyaient le client.
 *
 * Fichiers, support client, compta, marketing, RH, signature et developpement
 * sont volontairement SORTIS de la page principale : ils vivent dans « Tout
 * parcourir » et se trouvent par la recherche. Rien n'est cache, seulement
 * range derriere ce qui sert tous les jours.
 *
 * Ne rien ajouter ici sans le lui demander : chaque ligne a ete choisie.
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
		applications: ['gmail', 'googlecalendar', 'googledrive', 'googledocs', 'googlesheets']
	},
	{
		id: 'microsoft',
		libelle: 'Espace Microsoft',
		// SharePoint n'existe pas chez Composio : verifie, absent.
		applications: ['outlook', 'one_drive', 'microsoft_teams']
	},
	{
		id: 'discussion',
		libelle: 'Discussions & réunions',
		applications: ['zoom']
	},
	{
		id: 'agenda',
		libelle: 'Agenda',
		applications: ['calendly', 'cal']
	},
	{
		id: 'clients',
		libelle: 'Clients & ventes',
		applications: ['hubspot', 'salesforce']
	},
	{
		id: 'projets',
		libelle: 'Projets & tâches',
		applications: ['notion', 'airtable']
	},
	{
		id: 'reseaux',
		libelle: 'Réseaux sociaux',
		applications: ['linkedin', 'facebook', 'twitter', 'instagram', 'tiktok', 'youtube']
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
