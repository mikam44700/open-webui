/**
 * Fiches des applications mises en vitrine.
 *
 * Meme role que `INTEGRATION_FR` pour les integrations natives : une phrase
 * courte, trois etiquettes au plus, et ce que l'assistant sait reellement faire
 * une fois l'application branchee.
 *
 * Seules les applications de la vitrine ont une fiche. Le reste du catalogue —
 * un millier d'entrees — garde une carte compacte : ecrire mille descriptions a
 * la main serait faux dans six mois, et les inventer serait pire.
 *
 * Trois etiquettes maximum, verifie par un test. Au-dela, les cartes cessent
 * d'avoir la meme hauteur et la grille se deforme.
 */

export type Fiche = {
	/** Une phrase, ce que le client comprend d'un coup d'oeil. */
	desc: string;
	/** Trois au plus. */
	tags: string[];
	/** Ce que l'assistant fait une fois branche — contenu de la fenetre. */
	actions: string[];
};

export const FICHES: Record<string, Fiche> = {
	// ── Espace Google ────────────────────────────────────────
	gmail: {
		desc: 'Votre boîte Gmail, lue et écrite par l’assistant.',
		tags: ['Lire', 'Répondre', 'Rechercher'],
		actions: [
			'Retrouver un message ancien à partir d’une phrase approximative',
			'Résumer une conversation longue avant que vous y répondiez',
			'Rédiger et envoyer une réponse à votre place',
			'Trier et classer ce qui arrive'
		]
	},
	googlecalendar: {
		desc: 'Votre agenda Google : consultation et prise de rendez-vous.',
		tags: ['Consulter', 'Créer', 'Déplacer'],
		actions: [
			'Dire ce que vous avez de prévu cette semaine',
			'Trouver un créneau libre commun à plusieurs personnes',
			'Créer un rendez-vous et inviter les participants',
			'Déplacer ou annuler en prévenant les invités'
		]
	},
	googledrive: {
		desc: 'Vos fichiers Google Drive.',
		tags: ['Rechercher', 'Lire', 'Partager'],
		actions: [
			'Retrouver un document à partir de son contenu, pas de son nom',
			'Lire et résumer un fichier',
			'Créer un dossier et y ranger des fichiers',
			'Partager un document avec quelqu’un'
		]
	},
	googledocs: {
		desc: 'Vos documents Google Docs.',
		tags: ['Rédiger', 'Corriger', 'Résumer'],
		actions: [
			'Rédiger un document depuis vos instructions',
			'Reprendre un texte existant : ton, longueur, fautes',
			'Résumer un document long en quelques points'
		]
	},
	googlesheets: {
		desc: 'Vos tableaux Google Sheets.',
		tags: ['Lire', 'Remplir', 'Calculer'],
		actions: [
			'Lire un tableau et répondre à une question dessus',
			'Ajouter des lignes depuis un e-mail ou un document',
			'Faire un calcul ou un récapitulatif sur une colonne'
		]
	},

	// ── Espace Microsoft ─────────────────────────────────────
	outlook: {
		desc: 'Votre messagerie Outlook et son agenda.',
		tags: ['Lire', 'Répondre', 'Agenda'],
		actions: [
			'Retrouver et résumer un échange',
			'Rédiger et envoyer une réponse',
			'Consulter l’agenda et poser un rendez-vous'
		]
	},
	one_drive: {
		desc: 'Vos fichiers OneDrive.',
		tags: ['Rechercher', 'Lire', 'Partager'],
		actions: [
			'Retrouver un fichier par son contenu',
			'Lire et résumer un document',
			'Partager un fichier avec un collègue'
		]
	},
	microsoft_teams: {
		desc: 'Vos conversations et canaux Microsoft Teams.',
		tags: ['Lire', 'Écrire', 'Résumer'],
		actions: [
			'Résumer ce qui s’est dit dans un canal pendant votre absence',
			'Envoyer un message à une personne ou à une équipe',
			'Retrouver une décision prise dans une conversation'
		]
	},

	// ── Discussions & réunions ───────────────────────────────
	zoom: {
		desc: 'Vos réunions Zoom.',
		tags: ['Planifier', 'Inviter', 'Enregistrer'],
		actions: [
			'Créer une réunion et envoyer le lien aux participants',
			'Lister vos réunions à venir',
			'Récupérer l’enregistrement ou la transcription d’une réunion passée'
		]
	},

	// ── Agenda ───────────────────────────────────────────────
	calendly: {
		desc: 'Vos pages de réservation Calendly.',
		tags: ['Rendez-vous', 'Créneaux', 'Annuler'],
		actions: [
			'Lister les rendez-vous pris par vos clients',
			'Vérifier vos créneaux encore libres',
			'Annuler ou reprogrammer un rendez-vous'
		]
	},
	cal: {
		desc: 'Vos réservations Cal.com.',
		tags: ['Rendez-vous', 'Créneaux', 'Annuler'],
		actions: [
			'Lister les rendez-vous à venir',
			'Vérifier les créneaux disponibles',
			'Annuler ou déplacer une réservation'
		]
	},

	// ── Clients & ventes ─────────────────────────────────────
	hubspot: {
		desc: 'Vos contacts et affaires HubSpot.',
		tags: ['Contacts', 'Affaires', 'Notes'],
		actions: [
			'Retrouver la fiche d’un client et son historique',
			'Créer un contact depuis un e-mail reçu',
			'Faire avancer une affaire dans le tunnel',
			'Ajouter un compte rendu après un appel'
		]
	},
	salesforce: {
		desc: 'Vos comptes et opportunités Salesforce.',
		tags: ['Comptes', 'Opportunités', 'Notes'],
		actions: [
			'Retrouver un compte et ses échanges récents',
			'Créer ou mettre à jour une opportunité',
			'Consigner un compte rendu de rendez-vous'
		]
	},

	// ── Projets & tâches ─────────────────────────────────────
	notion: {
		desc: 'Vos pages et bases Notion.',
		tags: ['Rechercher', 'Rédiger', 'Bases'],
		actions: [
			'Retrouver une page à partir de son contenu',
			'Rédiger ou compléter une page',
			'Ajouter une entrée dans une base de données'
		]
	},
	airtable: {
		desc: 'Vos bases Airtable.',
		tags: ['Lire', 'Ajouter', 'Filtrer'],
		actions: [
			'Répondre à une question à partir d’une base',
			'Ajouter une ligne depuis un e-mail ou un formulaire',
			'Filtrer et récapituler des enregistrements'
		]
	},

	// ── Réseaux sociaux ──────────────────────────────────────
	linkedin: {
		desc: 'Votre présence LinkedIn.',
		tags: ['Publier', 'Profil', 'Messages'],
		actions: [
			'Rédiger et publier un post',
			'Préparer une série de publications à l’avance',
			'Consulter votre profil et vos messages'
		]
	},
	facebook: {
		desc: 'Votre page Facebook.',
		tags: ['Publier', 'Page', 'Commentaires'],
		actions: [
			'Publier sur votre page',
			'Lire et répondre aux commentaires',
			'Consulter les statistiques de vos publications'
		]
	},
	twitter: {
		desc: 'Votre compte X, anciennement Twitter.',
		tags: ['Publier', 'Répondre', 'Rechercher'],
		actions: [
			'Rédiger et publier un message',
			'Répondre aux mentions',
			'Chercher ce qui se dit sur un sujet'
		]
	},
	instagram: {
		desc: 'Votre compte Instagram professionnel.',
		tags: ['Publier', 'Commentaires', 'Statistiques'],
		actions: [
			'Publier une image avec sa légende',
			'Lire et répondre aux commentaires',
			'Consulter les statistiques d’un post'
		]
	},
	tiktok: {
		desc: 'Votre compte TikTok.',
		tags: ['Publier', 'Commentaires', 'Statistiques'],
		actions: [
			'Publier une vidéo avec sa description',
			'Suivre les commentaires',
			'Consulter les statistiques de vos vidéos'
		]
	},
	youtube: {
		desc: 'Votre chaîne YouTube.',
		tags: ['Publier', 'Commentaires', 'Statistiques'],
		actions: [
			'Mettre en ligne une vidéo et rédiger sa description',
			'Lire et répondre aux commentaires',
			'Consulter les vues et les statistiques d’une vidéo'
		]
	}
};

export const ficheDe = (slug: string): Fiche | null => FICHES[`${slug}`.toLowerCase()] ?? null;
