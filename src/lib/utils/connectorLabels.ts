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
	'data-gouv-fr': {
		name: 'data.gouv.fr',
		desc: 'Accès aux données publiques ouvertes de l’État français (data.gouv.fr). Souverain, gratuit, sans clé : la plateforme officielle est déjà hébergée.',
		popular: true,
		actions: [
			'Rechercher parmi les jeux de données publics de l’État',
			'Lire un fichier de données ouvert (CSV, Excel)',
			'Trouver les API officielles (entreprises SIRENE, adresses)',
			'Rechercher une administration ou un organisme public',
			'Consulter les statistiques d’un jeu de données'
		]
	},
	ableton: {
		name: 'Ableton Live',
		desc: 'Pilote Ableton Live depuis l’agent.',
		actions: [
			'Créer des pistes et des clips MIDI',
			'Régler les instruments et les effets',
			'Manipuler un Live Set',
			'Nécessite Ableton ouvert avec un pont script'
		]
	},
	alpaca: {
		name: 'Alpaca',
		desc: 'Trading actions et crypto (marché US).',
		actions: [
			'Passer des ordres actions, ETF, options et crypto',
			'Suivre et gérer un portefeuille',
			'Démarrer en environnement de test (« paper »)',
			'Relire chaque ordre avant exécution'
		]
	},
	aws: {
		name: 'AWS',
		desc: 'Point d’entrée aux services AWS.',
		actions: [
			'Accéder aux services AWS (EC2, S3, Lambda, RDS…)',
			'Serveur MCP officiel d’AWS Labs',
			'Restreindre les droits IAM au strict nécessaire'
		]
	},
	base: {
		name: 'Base',
		desc: 'Passerelle onchain de Coinbase (Base).',
		actions: [
			'Échanger des jetons et envoyer des fonds',
			'Suivre un portefeuille et utiliser la DeFi',
			'Non-custodial : vous signez chaque transaction'
		]
	},
	blender: {
		name: 'Blender',
		desc: 'Pilote le moteur 3D de Blender.',
		actions: [
			'Créer scènes, objets, matériaux et éclairage',
			'Piloter Blender par instructions',
			'Nécessite Blender ouvert avec l’add-on'
		]
	},
	ccxt: {
		name: 'CCXT',
		desc: 'Données de 20+ plateformes crypto.',
		actions: [
			'Lire les données de marché (Binance, Kraken, Bybit…)',
			'Accès unifié en lecture',
			'L’exécution d’ordres engage de l’argent réel (prudence)'
		]
	},
	cloudflare: {
		name: 'Cloudflare',
		desc: 'Gère votre infrastructure Cloudflare.',
		actions: [
			'Piloter Workers, DNS, R2, KV et Zero Trust',
			'Via l’API Cloudflare',
			'Autoriser et choisir les accès à la connexion'
		]
	},
	coingecko: {
		name: 'CoinGecko',
		desc: 'Prix et données du marché crypto.',
		actions: [
			'Consulter prix, capitalisations et historiques',
			'Serveur officiel CoinGecko',
			'Offre gratuite limitée (idéale pour la veille)'
		]
	},
	context7: {
		name: 'Context7',
		desc: 'Docs à jour des librairies pour l’agent.',
		actions: [
			'Récupérer la doc exacte d’une librairie',
			'Épinglée à la bonne version',
			'Évite les API inventées (hallucinations)'
		]
	},
	'davinci-resolve': {
		name: 'DaVinci Resolve',
		desc: 'Pilote DaVinci Resolve Studio.',
		actions: [
			'Montage timeline et gestion des médias',
			'Étalonnage, Fusion, Fairlight et rendu',
			'Nécessite Resolve ouvert (scripting local)'
		]
	},
	'docker-hub': {
		name: 'Docker Hub',
		desc: 'Cherche et gère des images Docker.',
		actions: [
			'Rechercher des images sur Docker Hub',
			'Gérer les tags',
			'Communautaire — relire avant un accès en écriture'
		]
	},
	dune: {
		name: 'Dune',
		desc: 'Requêtes Dune Analytics onchain.',
		actions: [
			'Lancer et lire des requêtes Dune',
			'Analyser des données onchain',
			'Crédits API comptés (offre gratuite limitée)'
		]
	},
	etherscan: {
		name: 'Etherscan',
		desc: 'Explorateur de blocs Ethereum.',
		actions: [
			'Vérifier des contrats et des transactions',
			'Récupérer des ABI',
			'Lecture seule, sans risque'
		]
	},
	fetch: {
		name: 'Fetch',
		desc: 'Récupère une page web en Markdown.',
		actions: [
			'Télécharger le contenu d’une URL',
			'Le convertir en Markdown pour l’agent'
		]
	},
	filesystem: {
		name: 'Filesystem',
		desc: 'Lit et écrit des fichiers locaux.',
		actions: [
			'Lire, écrire et chercher des fichiers',
			'Limité aux dossiers autorisés'
		]
	},
	git: {
		name: 'Git',
		desc: 'Gère des dépôts Git locaux.',
		actions: [
			'Lire et parcourir un dépôt',
			'Rechercher dans l’historique',
			'Manipuler les dépôts Git locaux'
		]
	},
	github: {
		name: 'GitHub',
		desc: 'Gère vos dépôts GitHub.',
		actions: [
			'Gérer dépôts, issues et pull requests',
			'Via l’API GitHub'
		]
	},
	kubernetes: {
		name: 'Kubernetes',
		desc: 'Inspecte un cluster en langage clair.',
		actions: [
			'Inspecter le cluster',
			'Opérations façon kubectl en langage naturel',
			'Communautaire — viser d’abord un contexte hors-prod'
		]
	},
	'meigen-ai-design': {
		name: 'MeiGen AI Design',
		desc: 'Génération d’images et de vidéos.',
		actions: [
			'9 modèles de pointe (GPT Image 2, Veo 3.1, Midjourney…)',
			'Créer des images et des vidéos',
			'Sécurisé (SSRF), fichiers auto-supprimés après 24 h'
		]
	},
	memory: {
		name: 'Memory',
		desc: 'Mémoire persistante entre les sessions.',
		actions: [
			'Mémoriser via un graphe de connaissances',
			'Retrouver le contexte d’une session à l’autre'
		]
	},
	mistral: {
		name: 'Mistral AI',
		desc: 'Toute la surface de Mistral AI.',
		actions: [
			'Chat, embeddings, vision et OCR',
			'Audio Voxtral (transcription et synthèse vocale)',
			'Agents, modération, fichiers et traitement par lots',
			'Offre gratuite : 1 milliard de tokens/mois'
		]
	},
	neon: {
		name: 'Neon',
		desc: 'Postgres serverless avec branches.',
		actions: [
			'Base Postgres serverless',
			'Migrations testées sur une branche instantanée',
			'Appliquées seulement une fois validées'
		]
	},
	playwright: {
		name: 'Playwright',
		desc: 'Pilote un vrai navigateur.',
		actions: [
			'Naviguer, cliquer et remplir des formulaires',
			'Faire des captures d’écran',
			'Lancer des tests en langage naturel'
		]
	},
	'polygon-io': {
		name: 'Polygon.io',
		desc: 'Données de marché financières.',
		actions: [
			'Flux actions, options, forex et crypto',
			'Agrégats et transactions',
			'Serveur officiel, données seules (pas d’exécution)'
		]
	},
	postgres: {
		name: 'Postgres',
		desc: 'Interroge une base PostgreSQL.',
		actions: ['Requêter et inspecter la base', 'Lecture seule']
	},
	puppeteer: {
		name: 'Puppeteer',
		desc: 'Pilote un navigateur sans interface.',
		actions: ['Naviguer et extraire des pages', 'Faire des captures d’écran']
	},
	redis: {
		name: 'Redis',
		desc: 'Inspecte une instance Redis.',
		actions: [
			'Consulter les clés',
			'Gérer les caches',
			'Surveiller la mémoire',
			'Serveur officiel Redis'
		]
	},
	sentry: {
		name: 'Sentry',
		desc: 'Remonte les erreurs de production.',
		actions: [
			'Lire issues, traces et détails d’un incident',
			'Proposer un correctif',
			'Se marie bien avec GitHub'
		]
	},
	'sequential-thinking': {
		name: 'Sequential Thinking',
		desc: 'Raisonnement étape par étape.',
		actions: [
			'Brouillon de réflexion structuré',
			'Idéal pour les problèmes difficiles'
		]
	},
	'solana-agent-kit': {
		name: 'Solana Agent Kit',
		desc: 'Actions onchain sur Solana.',
		actions: [
			'Transferts, swaps et opérations sur jetons',
			'Chaîne irréversible : prudence',
			'Préférer un wallet dédié pour signer'
		]
	},
	sqlite: {
		name: 'SQLite',
		desc: 'Interroge une base SQLite locale.',
		actions: ['Requêter et inspecter la base locale']
	},
	supabase: {
		name: 'Supabase',
		desc: 'Gère votre backend Supabase.',
		actions: [
			'Base de données, authentification, stockage et edge functions',
			'Piloter par le chat',
			'Commencer en lecture seule'
		]
	},
	'the-graph': {
		name: 'The Graph',
		desc: 'Données onchain via des subgraphs.',
		actions: [
			'Interroger des données onchain',
			'Sans faire tourner d’indexeur',
			'Lecture seule, faible risque'
		]
	},
	thirdweb: {
		name: 'thirdweb',
		desc: 'Contrats intelligents multi-chaînes EVM.',
		actions: [
			'Déployer et utiliser des contrats',
			'Sur les chaînes EVM',
			'Déploiements irréversibles : tester en testnet'
		]
	},
	tradingview: {
		name: 'TradingView',
		desc: 'Graphiques et données de marché.',
		actions: [
			'Contexte marché depuis TradingView',
			'Communautaire (scraping) — fragile aux changements',
			'À considérer comme « au mieux »'
		]
	},
	vercel: {
		name: 'Vercel',
		desc: 'Inspecte vos déploiements Vercel.',
		actions: [
			'Voir les déploiements',
			'Gérer les variables d’environnement',
			'Lire les logs',
			'Garder un humain dans la boucle sur ce qui part en prod'
		]
	},
	crawl4ai: {
		name: 'Crawl4AI',
		desc: 'Lecture web approfondie, souveraine et gratuite : l’agent lit une page en entier et en extrait l’essentiel proprement. Tourne sur votre machine, sans dépendre d’un service externe.',
		popular: true,
		actions: [
			'Lire une page web et en extraire le texte propre (sans pub ni menus)',
			'Capturer une page en image',
			'Enregistrer une page en PDF',
			'Explorer une page complexe (boutons, contenu qui se charge)',
			'Récupérer des informations précises sur une page'
		]
	},
	hubspot: {
		name: 'HubSpot',
		desc: 'Votre CRM HubSpot, piloté depuis l’agent.',
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
		desc: 'Tickets et projets Linear, depuis l’agent.',
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
		desc: 'Pilote vos workflows d’automatisation n8n.',
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
		desc: 'Pilote l’éditeur Unreal Engine en local.',
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
