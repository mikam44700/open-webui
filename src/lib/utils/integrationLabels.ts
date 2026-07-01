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
	// `actions` = ce que l'intégration permet une fois branchée (déroulant « Voir ce que ça fait »).
	actions?: string[];
};

export const INTEGRATION_FR: Record<string, IntegrationMeta> = {
	'google-workspace': {
		name: 'Google Workspace',
		desc: 'Gmail, Agenda, Drive et Docs, depuis l’agent.',
		category: 'Productivité',
		popular: true,
		actions: [
			'Lire et envoyer des e-mails (Gmail)',
			'Gérer l’agenda et les événements',
			'Chercher et créer des fichiers (Drive, Docs, Sheets)',
			'Consulter les contacts'
		]
	},
	notion: {
		name: 'Notion',
		desc: 'Vos pages et bases Notion, depuis l’agent.',
		category: 'Productivité',
		popular: true,
		actions: [
			'Chercher et lire des pages',
			'Créer et mettre à jour des pages',
			'Interroger des bases de données'
		]
	},
	github: {
		name: 'GitHub',
		desc: 'Vos dépôts, issues et pull requests GitHub.',
		category: 'Développement',
		actions: [
			'Parcourir dépôts et fichiers',
			'Créer et suivre des issues',
			'Gérer les pull requests'
		]
	},
	airtable: {
		name: 'Airtable',
		desc: 'Vos bases Airtable, depuis l’agent.',
		category: 'Productivité',
		popular: true,
		actions: [
			'Lire tables et enregistrements',
			'Créer et mettre à jour des enregistrements',
			'Filtrer et parcourir des vues'
		]
	},
	email: {
		name: 'Email',
		desc: 'Votre boîte mail (réception et envoi).',
		category: 'Communication',
		actions: [
			'Lire les e-mails reçus',
			'Rechercher dans la boîte',
			'Rédiger et envoyer des e-mails',
			'Via IMAP/SMTP'
		]
	},
	obsidian: {
		name: 'Obsidian',
		desc: 'Votre coffre de notes Obsidian.',
		category: 'Productivité',
		popular: true,
		actions: [
			'Lire et chercher des notes',
			'Créer de nouvelles notes',
			'Lier les notes entre elles'
		]
	},
	x: {
		name: 'X (Twitter)',
		desc: 'Publier et lire sur X, avec votre compte.',
		category: 'Réseaux sociaux',
		actions: ['Publier des posts', 'Rechercher des posts et fils', 'Lire votre fil']
	},
	apple: {
		name: 'Apple',
		desc: 'Notes, Rappels et iMessage sur Mac.',
		category: 'Productivité',
		actions: [
			'Créer notes et rappels',
			'Envoyer des iMessages',
			'Fonctionne en local sur votre Mac'
		]
	},
	hue: {
		name: 'Philips Hue',
		desc: 'Pilote vos lumières Philips Hue.',
		category: 'Maison',
		actions: [
			'Allumer et éteindre les lumières',
			'Régler l’intensité et la couleur',
			'Piloter par pièce ou par scène'
		]
	},
	'microsoft-365': {
		name: 'Microsoft 365',
		desc: 'Outlook, Teams, OneDrive et Office.',
		category: 'Productivité',
		popular: true,
		actions: [
			'Lire et envoyer des e-mails (Outlook)',
			'Gérer l’agenda et les réunions Teams',
			'Fichiers OneDrive, Word, Excel, PowerPoint',
			'Consulter les contacts'
		]
	},
	calendly: {
		name: 'Calendly',
		desc: 'Prise de rendez-vous automatisée.',
		category: 'Productivité',
		popular: true,
		actions: [
			'Partager votre lien de réservation',
			'Consulter vos disponibilités',
			'Suivre les rendez-vous pris'
		]
	},
	box: {
		name: 'Box',
		desc: 'Stockage de fichiers sécurisé (Box).',
		category: 'Productivité',
		actions: [
			'Parcourir fichiers et dossiers',
			'Téléverser et télécharger des fichiers',
			'Partager des documents'
		]
	},
	dropbox: {
		name: 'Dropbox',
		desc: 'Stockage et synchro de fichiers Dropbox.',
		category: 'Productivité',
		actions: [
			'Parcourir fichiers et dossiers',
			'Téléverser et télécharger',
			'Partager des liens'
		]
	},
	salesforce: {
		name: 'Salesforce',
		desc: 'Votre CRM Salesforce, depuis l’agent.',
		category: 'Productivité',
		actions: [
			'Rechercher contacts et comptes',
			'Suivre les opportunités',
			'Créer et mettre à jour des fiches'
		]
	},
	clickup: {
		name: 'ClickUp',
		desc: 'Projets et tâches ClickUp.',
		category: 'Productivité',
		actions: [
			'Créer et suivre des tâches',
			'Gérer statuts et assignations',
			'Parcourir listes et projets'
		]
	},
	'google-meet': {
		name: 'Google Meet',
		desc: 'Réunions vidéo Google Meet.',
		category: 'Communication',
		actions: [
			'Créer des réunions Meet',
			'Générer le lien visio',
			'Via votre compte Google'
		]
	},
	'google-slides': {
		name: 'Google Slides',
		desc: 'Présentations Google Slides.',
		category: 'Productivité',
		actions: [
			'Créer des présentations',
			'Gérer les diapositives',
			'Via votre compte Google'
		]
	},
	'google-analytics': {
		name: 'Google Analytics',
		desc: 'Fréquentation de votre site.',
		category: 'Productivité',
		actions: [
			'Consulter l’audience du site',
			'Suivre les tendances de trafic',
			'Lecture seule, via Google'
		]
	},
	'google-search-console': {
		name: 'Google Search Console',
		desc: 'Référencement de votre site (Google).',
		category: 'Productivité',
		actions: [
			'Voir les requêtes de recherche',
			'Suivre l’indexation du site',
			'Lecture seule, via Google'
		]
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
