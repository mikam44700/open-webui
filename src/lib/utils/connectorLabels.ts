// Descriptions FR + actions des connecteurs MCP du catalogue Hermes (orientées client,
// sans jargon). Source unique partagée par les cartes du catalogue, pour franciser les
// descriptions techniques renvoyées par Hermes (souvent en anglais) sans toucher au moteur.
//
// `actions` = ce que le connecteur permet de faire une fois branché. Liste indicative :
// la liste exacte des outils exposés dépend de la version du serveur MCP et se confirme
// après installation (cf. règle d'honnêteté des libellés).

export const CONNECTOR_FR: Record<
	string,
	{ name: string; desc: string; actions: string[]; popular?: boolean }
> = {
	hubspot: {
		name: 'HubSpot',
		desc: 'Connecte ton CRM HubSpot : contacts, entreprises, transactions et tickets, pilotés depuis l’agent.',
		popular: true,
		actions: [
			'Rechercher contacts, entreprises et transactions',
			'Créer ou mettre à jour une fiche contact / entreprise',
			'Suivre l’avancement des transactions (deals)',
			'Consulter et créer des tickets de support',
			'Lire l’activité récente du CRM'
		]
	},
	linear: {
		name: 'Linear',
		desc: 'Gère tes tickets, projets et commentaires Linear (gestion de projet) directement depuis l’agent.',
		actions: [
			'Rechercher et lister tickets, projets et équipes',
			'Créer un ticket (titre, description, priorité)',
			'Mettre à jour un ticket (statut, assigné, étiquettes)',
			'Lire et ajouter des commentaires',
			'Consulter les projets et les cycles'
		]
	},
	n8n: {
		name: 'N8N',
		desc: 'Pilote et inspecte tes workflows d’automatisation n8n, via un pont local (sans port public exposé).',
		actions: [
			'Lister les workflows existants',
			'Inspecter le détail d’un workflow (nœuds, connexions)',
			'Déclencher / exécuter un workflow',
			'Activer ou désactiver un workflow',
			'Consulter l’historique des exécutions'
		]
	},
	'unreal-engine': {
		name: 'Unreal Engine',
		desc: 'Pilote l’éditeur Unreal Engine 5.8 en local : manipulation de la scène et automatisation de l’éditeur.',
		actions: [
			'Créer, déplacer et supprimer des acteurs dans la scène',
			'Inspecter et modifier les propriétés des objets',
			'Exécuter des commandes Python de l’éditeur',
			'Manipuler les assets et les Blueprints',
			'Contrôler le viewport et la caméra'
		]
	},

	// --- Productivité & Bureau (visibles) ---
	gmail: {
		name: 'Gmail',
		desc: 'Lis et envoie tes e-mails Gmail directement depuis l’agent.',
		popular: true,
		actions: ['Lire et rechercher des e-mails', 'Rédiger et envoyer un message', 'Trier et organiser la boîte de réception']
	},
	'google-calendar': {
		name: 'Google Calendar',
		desc: 'Consulte ton agenda, planifie des rendez-vous et vérifie tes disponibilités.',
		actions: ['Voir les événements à venir', 'Créer un rendez-vous', 'Vérifier les créneaux libres']
	},
	'google-drive': {
		name: 'Google Drive',
		desc: 'Recherche et lit tes fichiers et documents stockés sur Google Drive.',
		actions: ['Rechercher un fichier', 'Lire le contenu d’un document', 'Parcourir les dossiers']
	},
	notion: {
		name: 'Notion',
		desc: 'Lis et met à jour tes pages et bases de données Notion.',
		popular: true,
		actions: ['Rechercher dans l’espace Notion', 'Lire une page', 'Créer ou mettre à jour une page / un enregistrement']
	},
	slack: {
		name: 'Slack',
		desc: 'Lis et publie des messages dans tes canaux Slack.',
		actions: ['Lire les messages d’un canal', 'Publier un message', 'Rechercher dans l’historique']
	},
	asana: {
		name: 'Asana',
		desc: 'Gère tes tâches, projets et charge de travail dans Asana.',
		actions: ['Lister tâches et projets', 'Créer une tâche', 'Mettre à jour le statut d’une tâche']
	},
	atlassian: {
		name: 'Jira & Confluence',
		desc: 'Pilote tes tickets Jira et tes documents Confluence (suite Atlassian).',
		actions: ['Rechercher et créer des tickets Jira', 'Mettre à jour un ticket', 'Lire des pages Confluence']
	},
	airtable: {
		name: 'Airtable',
		desc: 'Lis et écris des enregistrements et des bases dans Airtable.',
		actions: ['Lister les enregistrements d’une base', 'Créer ou modifier un enregistrement', 'Consulter la structure d’une base']
	},
	youtube: {
		name: 'YouTube',
		desc: 'Recherche des vidéos et récupère leurs transcriptions (recherche, veille, repurposing).',
		actions: ['Rechercher des vidéos', 'Récupérer la transcription d’une vidéo', 'Résumer le contenu']
	},

	// --- Finance (visibles) ---
	stripe: {
		name: 'Stripe',
		desc: 'Paiements, abonnements, remboursements et fiches clients via le serveur officiel Stripe.',
		popular: true,
		actions: ['Consulter paiements et abonnements', 'Émettre un remboursement', 'Rechercher un client']
	},
	paypal: {
		name: 'PayPal',
		desc: 'Factures, transactions et versements via la boîte à outils officielle PayPal.',
		actions: ['Créer et envoyer une facture', 'Consulter les transactions', 'Lancer un versement']
	},
	quickbooks: {
		name: 'QuickBooks',
		desc: 'Comptabilité, facturation et rapprochement via QuickBooks (Intuit).',
		actions: ['Créer une facture', 'Consulter les écritures', 'Rapprocher les comptes']
	},
	plaid: {
		name: 'Plaid',
		desc: 'Données bancaires, soldes et transactions via le serveur officiel Plaid.',
		actions: ['Consulter les soldes de comptes', 'Lister les transactions', 'Agréger les données bancaires']
	},

	// --- Création & Média (visibles) ---
	canva: {
		name: 'Canva',
		desc: 'Génère et modifie des designs à partir de modèles dans Canva.',
		actions: ['Créer un design depuis un modèle', 'Modifier un design existant', 'Exporter un visuel']
	},
	figma: {
		name: 'Figma',
		desc: 'Lis composants, variables et maquettes Figma, et génère du code depuis les écrans.',
		actions: ['Lire une maquette et ses composants', 'Récupérer les variables de design', 'Générer du code depuis un écran']
	},
	elevenlabs: {
		name: 'ElevenLabs',
		desc: 'Synthèse vocale et audio : génère de la voix, clone une voix, transcris (serveur officiel).',
		actions: ['Générer une voix à partir d’un texte', 'Cloner une voix', 'Transcrire un audio']
	},
	higgsfield: {
		name: 'Higgsfield',
		desc: 'Plus de 30 modèles d’image et de vidéo (Sora, Veo, Kling, Seedance) via un seul accès.',
		actions: ['Générer une image', 'Générer une vidéo', 'Choisir parmi plusieurs modèles']
	},

	// --- Recherche (visible) ---
	'brave-search': {
		name: 'Brave Search',
		desc: 'Recherche web et locale via l’API Brave Search.',
		popular: true,
		actions: ['Rechercher sur le web', 'Recherche locale (lieux, commerces)']
	}
};
