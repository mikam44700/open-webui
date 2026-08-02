/**
 * Classement metier des applications Composio.
 *
 * Composio en propose plus de mille, rangees par ordre alphabetique. Presentees
 * telles quelles, elles commencent par « 1password, 21risk, 2chat, Ably » : un
 * dirigeant n'y trouve jamais sa messagerie. On garde donc la meme approche que
 * pour les fournisseurs de modeles (lib/catalog/provider-taxonomy.ts) : un
 * classement maison, en francais, oriente usage.
 *
 * Cette liste est celle de Mike, arretee le 2 aout 2026 : seize applications,
 * cinq categories, dans son ordre. Elle est volontairement COURTE. Tout ce qui
 * n'y figure pas reste atteignable par la recherche et par le reste du
 * catalogue — rien n'est cache, seulement range derriere ce qui sert tous les
 * jours. Ne pas rallonger sans le lui demander.
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
		id: 'messagerie',
		libelle: 'Messagerie',
		applications: ['gmail', 'outlook']
	},
	{
		id: 'agenda',
		libelle: 'Agenda',
		applications: ['googlecalendar', 'calendly', 'cal']
	},
	{
		id: 'fichiers',
		libelle: 'Fichiers et documents',
		applications: ['googledrive', 'one_drive', 'dropbox']
	},
	{
		id: 'reseaux',
		libelle: 'Réseaux sociaux',
		applications: ['linkedin', 'facebook', 'twitter', 'instagram', 'tiktok', 'youtube']
	},
	{
		id: 'projets',
		libelle: 'Projets et tâches',
		applications: ['airtable', 'notion']
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
	dropbox_sign: 'Dropbox Sign'
};

export const nomAffiche = (slug: string, nomComposio: string): string =>
	NOMS_FR[slug] ?? nomComposio;
