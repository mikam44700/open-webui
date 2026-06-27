// Nom + description FR des intégrations (orientés client, sans jargon), partagés par
// l'onglet Intégrations. Même principe que connectorLabels.ts.
//
// `name` : nom affiché · `desc` : à quoi ça sert, en clair · les sous-services viennent
// du backend (catalogue Hermes), pas d'ici.

export type IntegrationMeta = {
	name: string;
	desc: string;
	// Catégorie (filtre de la modale « Parcourir ») et mise en avant (section « Les plus populaires »).
	category?: string;
	popular?: boolean;
};

export const INTEGRATION_FR: Record<string, IntegrationMeta> = {
	'google-workspace': {
		name: 'Google Workspace',
		desc: 'Gmail, Agenda, Drive, Sheets et Docs — branchés sur ton compte Google.',
		category: 'Productivité',
		popular: true
	},
	notion: {
		name: 'Notion',
		desc: 'Tes pages, bases de données et notes Notion, accessibles par l’agent.',
		category: 'Productivité',
		popular: true
	},
	github: {
		name: 'GitHub',
		desc: 'Tes dépôts, issues et pull requests GitHub.',
		category: 'Développement',
		popular: true
	},
	airtable: {
		name: 'Airtable',
		desc: 'Tes bases Airtable : tables, enregistrements et vues.',
		category: 'Productivité',
		popular: true
	},
	email: {
		name: 'Email',
		desc: 'Ta boîte mail (réception et envoi) via IMAP/SMTP.',
		category: 'Communication'
	},
	obsidian: {
		name: 'Obsidian',
		desc: 'Ton coffre de notes Obsidian : lire, chercher, créer et lier des notes.',
		category: 'Productivité'
	},
	x: {
		name: 'X (Twitter)',
		desc: 'Publier, rechercher et lire sur X avec ton compte.',
		category: 'Réseaux sociaux'
	},
	apple: {
		name: 'Apple',
		desc: 'Notes, Rappels et iMessage — sur ton Mac.',
		category: 'Productivité'
	},
	hue: {
		name: 'Philips Hue',
		desc: 'Pilote tes lumières connectées Philips Hue.',
		category: 'Maison'
	},
	'microsoft-365': {
		name: 'Microsoft 365',
		desc: 'Outlook, OneDrive, Teams, Agenda — toute votre suite bureautique.',
		category: 'Productivité',
		popular: true
	}
};

// Ordre d'affichage des catégories dans le filtre de la modale « Parcourir ».
export const INTEGRATION_CATEGORIES = [
	'Productivité',
	'Communication',
	'Développement',
	'Réseaux sociaux',
	'Maison'
];

// Accès en langage client (pas de jargon : ni « OAuth », ni « IMAP »).
export const ACCESS_LABEL: Record<string, string> = {
	account: 'Connexion par compte',
	key: 'Clé requise',
	credentials: 'Identifiants requis',
	path: 'Dossier à indiquer',
	local: 'Sur cet appareil'
};

// Libellés d'état honnêtes (jamais d'état supposé).
export const STATE_LABEL: Record<string, string> = {
	not_connected: 'Non connecté',
	key_present: 'Clé enregistrée',
	connected: 'Connecté',
	error: 'Erreur',
	unavailable: 'Indisponible'
};
