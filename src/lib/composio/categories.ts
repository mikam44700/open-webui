/**
 * Classement metier des applications Composio.
 *
 * Composio en propose plus de mille, rangees par ordre alphabetique. Presentees
 * telles quelles, elles commencent par « 1password, 21risk, 2chat, Ably » : un
 * dirigeant n'y trouve jamais sa messagerie. On garde donc la meme approche que
 * pour les fournisseurs de modeles (lib/catalog/provider-taxonomy.ts) : un
 * classement maison, en francais, oriente usage.
 *
 * Ce catalogue est volontairement COURT. Tout ce qui n'y figure pas reste
 * atteignable par la recherche et par « Tout parcourir » — rien n'est cache,
 * seulement range derriere ce qui sert tous les jours.
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
		libelle: 'Messagerie & agenda',
		applications: ['gmail', 'outlook', 'googlecalendar', 'calendly', 'cal', 'googlemeet', 'zoom']
	},
	{
		id: 'fichiers',
		libelle: 'Fichiers & documents',
		applications: [
			'googledrive',
			'one_drive',
			'dropbox',
			'box',
			'googledocs',
			'googlesheets',
			'notion',
			'docusign',
			'dropbox_sign'
		]
	},
	{
		id: 'equipe',
		libelle: 'Discussion d’équipe',
		applications: ['slack', 'microsoft_teams', 'discord', 'whatsapp']
	},
	{
		id: 'clients',
		libelle: 'Clients & ventes',
		applications: ['hubspot', 'salesforce', 'pipedrive', 'attio', 'mailchimp']
	},
	{
		id: 'projets',
		libelle: 'Projets & tâches',
		applications: ['linear', 'asana', 'trello', 'clickup', 'jira', 'monday', 'airtable']
	},
	{
		id: 'reseaux',
		libelle: 'Réseaux sociaux',
		applications: ['linkedin', 'twitter', 'facebook', 'instagram', 'tiktok', 'youtube']
	},
	{
		id: 'compta',
		libelle: 'Compta & paiement',
		applications: ['stripe', 'paypal', 'quickbooks', 'xero']
	},
	{
		id: 'developpement',
		libelle: 'Développement & design',
		// `figma` et `linear` existent aussi chez Composio, mais le moteur porte
		// deja ses propres serveurs MCP pour eux : les mettre ici en ferait un
		// doublon, et le doublon Composio serait facture a l'appel. Ils restent
		// trouvables par la recherche — declasses, pas caches.
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
	dropbox_sign: 'Dropbox Sign'
};

export const nomAffiche = (slug: string, nomComposio: string): string =>
	NOMS_FR[slug] ?? nomComposio;
