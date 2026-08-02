/**
 * Ce que l'assistant sait faire, pour les applications du catalogue recommande.
 *
 * `fiches.ts` couvre les vingt-trois de la vitrine. Les deux cent quatre-vingt-
 * quinze autres tombaient sur le texte anglais de Composio des qu'on ouvrait
 * « Voir ce que ca fait » — dans un produit vendu en francais.
 *
 * Trois etiquettes, trois actions. Court : la fenetre explique, elle ne raconte
 * pas. La phrase d'accroche, elle, vit dans `descriptions.ts`.
 */

export type FicheCatalogue = {
	tags: string[];
	actions: string[];
};

export const FICHES_CATALOGUE: Record<string, FicheCatalogue> = {
	// ── Messagerie & discussion ──────────────────────────────
	google_chat: {
		tags: ['Lire', 'Écrire', 'Résumer'],
		actions: [
			'Résumer ce qui s’est dit dans un espace',
			'Envoyer un message à une personne ou à un espace',
			'Retrouver un échange ancien'
		]
	},
	discord: {
		tags: ['Lire', 'Écrire', 'Modérer'],
		actions: [
			'Publier un message dans un salon',
			'Lire ce qui s’est dit pendant votre absence',
			'Répondre aux membres de votre communauté'
		]
	},
	telegram: {
		tags: ['Écrire', 'Robots', 'Diffuser'],
		actions: [
			'Envoyer un message à une personne ou à un groupe',
			'Diffuser une annonce à vos abonnés',
			'Faire réagir un robot à vos messages'
		]
	},
	whatsapp: {
		tags: ['Écrire', 'Clients', 'Modèles'],
		actions: [
			'Répondre à un client sur WhatsApp',
			'Envoyer une confirmation ou un rappel',
			'Suivre les conversations en cours'
		]
	},
	chatwork: {
		tags: ['Lire', 'Écrire', 'Tâches'],
		actions: [
			'Envoyer un message à un groupe',
			'Résumer une discussion d’équipe',
			'Créer une tâche depuis un message'
		]
	},
	missive: {
		tags: ['Lire', 'Répondre', 'Attribuer'],
		actions: [
			'Traiter une boîte mail partagée',
			'Rédiger une réponse au nom de l’équipe',
			'Attribuer une conversation à quelqu’un'
		]
	},
	zulip: {
		tags: ['Lire', 'Écrire', 'Résumer'],
		actions: [
			'Suivre un fil de discussion précis',
			'Publier dans un canal',
			'Résumer un sujet en cours'
		]
	},
	respond_io: {
		tags: ['Clients', 'Répondre', 'Suivre'],
		actions: [
			'Répondre à un client, quel que soit son canal',
			'Retrouver l’historique d’une conversation',
			'Passer la main à un collègue'
		]
	},
	wati: {
		tags: ['WhatsApp', 'Clients', 'Diffuser'],
		actions: [
			'Répondre aux clients sur WhatsApp',
			'Envoyer une campagne à vos contacts',
			'Suivre les conversations non traitées'
		]
	},

	// ── Réunions ─────────────────────────────────────────────
	webex: {
		tags: ['Planifier', 'Inviter', 'Rejoindre'],
		actions: [
			'Créer une réunion et envoyer le lien',
			'Lister vos réunions à venir',
			'Récupérer les informations d’une réunion passée'
		]
	},
	clickmeeting: {
		tags: ['Webinaires', 'Inscrits', 'Statistiques'],
		actions: [
			'Créer un webinaire et ouvrir les inscriptions',
			'Récupérer la liste des inscrits',
			'Consulter la participation après coup'
		]
	},
	demio: {
		tags: ['Webinaires', 'Inscrits', 'Suivi'],
		actions: [
			'Programmer un webinaire',
			'Inscrire un contact automatiquement',
			'Savoir qui est venu et qui a manqué'
		]
	},
	fireflies: {
		tags: ['Transcrire', 'Résumer', 'Rechercher'],
		actions: [
			'Récupérer la transcription d’une réunion',
			'En sortir un résumé et les décisions prises',
			'Retrouver un passage précis dans vos réunions'
		]
	},
	tldv: {
		tags: ['Enregistrer', 'Transcrire', 'Résumer'],
		actions: [
			'Récupérer l’enregistrement d’une visio',
			'Lire la transcription',
			'Résumer ce qui s’est dit'
		]
	},
	recallai: {
		tags: ['Réunions', 'Transcrire', 'Données'],
		actions: [
			'Récupérer le contenu d’une réunion',
			'Obtenir la transcription horodatée',
			'Suivre plusieurs plateformes de visio'
		]
	},
	granola_mcp: {
		tags: ['Notes', 'Réunions', 'Résumer'],
		actions: [
			'Retrouver vos notes de réunion',
			'Résumer une réunion passée',
			'En extraire les prochaines actions'
		]
	},

	// ── Agenda & rendez-vous ─────────────────────────────────
	scheduleonce: {
		tags: ['Rendez-vous', 'Créneaux', 'Prospects'],
		actions: [
			'Voir les rendez-vous pris par vos prospects',
			'Vérifier vos disponibilités',
			'Annuler ou déplacer un rendez-vous'
		]
	},
	supersaas: {
		tags: ['Réservations', 'Créneaux', 'Annuler'],
		actions: [
			'Lister les réservations à venir',
			'Vérifier les créneaux libres',
			'Annuler une réservation'
		]
	},
	appointo: {
		tags: ['Rendez-vous', 'Boutique', 'Créneaux'],
		actions: [
			'Voir les rendez-vous pris depuis votre boutique',
			'Vérifier les créneaux disponibles',
			'Déplacer un rendez-vous'
		]
	},
	etermin: {
		tags: ['Rendez-vous', 'Créneaux', 'Clients'],
		actions: [
			'Lister les rendez-vous du jour',
			'Vérifier les disponibilités',
			'Annuler ou reprogrammer'
		]
	},
	calendarhero: {
		tags: ['Rendez-vous', 'Créneaux', 'Relances'],
		actions: [
			'Proposer un créneau à plusieurs personnes',
			'Programmer un rendez-vous automatiquement',
			'Relancer un invité qui n’a pas répondu'
		]
	},
	motion: {
		tags: ['Agenda', 'Tâches', 'Priorités'],
		actions: [
			'Ajouter une tâche et la placer dans votre journée',
			'Voir ce qui est prévu aujourd’hui',
			'Replanifier ce qui a pris du retard'
		]
	},
	ticktick: {
		tags: ['Tâches', 'Listes', 'Rappels'],
		actions: [
			'Ajouter une tâche avec sa date',
			'Lister ce qui est à faire aujourd’hui',
			'Marquer une tâche comme terminée'
		]
	},
	todoist: {
		tags: ['Tâches', 'Projets', 'Rappels'],
		actions: [
			'Ajouter une tâche depuis un e-mail',
			'Lister ce qui est en retard',
			'Terminer ou reporter une tâche'
		]
	},
	microsoft_todo: {
		tags: ['Tâches', 'Listes', 'Rappels'],
		actions: [
			'Ajouter une tâche à une liste',
			'Voir ce qui est prévu aujourd’hui',
			'Cocher une tâche terminée'
		]
	},

	// ── Fichiers & documents ─────────────────────────────────
	dropbox: {
		tags: ['Rechercher', 'Lire', 'Partager'],
		actions: [
			'Retrouver un fichier par son contenu',
			'Lire et résumer un document',
			'Partager un dossier avec quelqu’un'
		]
	},
	box: {
		tags: ['Rechercher', 'Lire', 'Partager'],
		actions: [
			'Retrouver un document par son contenu',
			'Lire et résumer un fichier',
			'Partager un dossier'
		]
	},
	egnyte: {
		tags: ['Rechercher', 'Lire', 'Partager'],
		actions: [
			'Retrouver un document par son contenu',
			'Lire et résumer un fichier',
			'Partager un dossier avec quelqu’un'
		]
	},
	share_point: {
		tags: ['Rechercher', 'Lire', 'Partager'],
		actions: [
			'Retrouver un document dans vos sites',
			'Lire et résumer un fichier',
			'Déposer un document au bon endroit'
		]
	},
	sharepoint_graph: {
		tags: ['Rechercher', 'Listes', 'Fichiers'],
		actions: [
			'Parcourir vos sites et bibliothèques',
			'Lire une liste SharePoint',
			'Récupérer un document précis'
		]
	},
	googleslides: {
		tags: ['Créer', 'Modifier', 'Résumer'],
		actions: [
			'Créer une présentation depuis vos notes',
			'Ajouter ou reprendre une diapositive',
			'Résumer une présentation existante'
		]
	},
	onenote: {
		tags: ['Rechercher', 'Rédiger', 'Carnets'],
		actions: [
			'Retrouver une note par son contenu',
			'Ajouter une page à un carnet',
			'Résumer un carnet entier'
		]
	},
	coda: {
		tags: ['Rechercher', 'Rédiger', 'Tables'],
		actions: [
			'Retrouver une page Coda',
			'Ajouter une ligne dans une table',
			'Rédiger ou compléter un document'
		]
	},
	excel: {
		tags: ['Lire', 'Remplir', 'Calculer'],
		actions: [
			'Répondre à une question sur un classeur',
			'Ajouter des lignes à une feuille',
			'Faire un récapitulatif sur une colonne'
		]
	},
	googlephotos: {
		tags: ['Rechercher', 'Albums', 'Partager'],
		actions: ['Retrouver une photo par sa description', 'Créer un album', 'Partager une sélection']
	},

	// ── CRM & ventes ─────────────────────────────────────────
	salesforce_service_cloud: {
		tags: ['Tickets', 'Clients', 'Notes'],
		actions: [
			'Retrouver le dossier d’un client',
			'Créer ou faire avancer un ticket',
			'Consigner un échange'
		]
	},
	pipedrive: {
		tags: ['Affaires', 'Contacts', 'Notes'],
		actions: [
			'Retrouver une affaire et son historique',
			'La faire avancer dans le tunnel',
			'Ajouter une note après un appel'
		]
	},
	attio: {
		tags: ['Contacts', 'Affaires', 'Notes'],
		actions: [
			'Retrouver une fiche entreprise',
			'Créer un contact depuis un e-mail',
			'Mettre à jour une affaire'
		]
	},
	close: {
		tags: ['Prospects', 'Appels', 'Affaires'],
		actions: [
			'Retrouver un prospect et ses échanges',
			'Consigner un appel',
			'Faire avancer une opportunité'
		]
	},
	folk: {
		tags: ['Contacts', 'Relances', 'Notes'],
		actions: [
			'Retrouver un contact et son historique',
			'Ajouter une note ou une relance',
			'Mettre à jour une fiche'
		]
	},
	capsule_crm: {
		tags: ['Contacts', 'Affaires', 'Tâches'],
		actions: [
			'Retrouver un contact',
			'Créer ou modifier une opportunité',
			'Ajouter une tâche de suivi'
		]
	},
	nutshell: {
		tags: ['Contacts', 'Affaires', 'Notes'],
		actions: [
			'Retrouver un client et ses échanges',
			'Faire avancer une affaire',
			'Consigner un compte rendu'
		]
	},
	zoho: {
		tags: ['Contacts', 'Affaires', 'Notes'],
		actions: [
			'Retrouver une fiche client',
			'Créer ou mettre à jour une opportunité',
			'Ajouter une note de suivi'
		]
	},
	zoho_bigin: {
		tags: ['Contacts', 'Pipeline', 'Notes'],
		actions: ['Retrouver un contact', 'Faire avancer une affaire', 'Ajouter une note']
	},
	kommo: {
		tags: ['Messages', 'Affaires', 'Contacts'],
		actions: [
			'Retrouver une conversation client',
			'Faire avancer une affaire',
			'Créer un contact depuis un message'
		]
	},
	espocrm: {
		tags: ['Contacts', 'Affaires', 'Notes'],
		actions: [
			'Retrouver un compte et ses contacts',
			'Créer ou modifier une opportunité',
			'Consigner un échange'
		]
	},
	salesflare: {
		tags: ['Contacts', 'Affaires', 'Suivi'],
		actions: [
			'Retrouver un client et son historique',
			'Faire avancer une affaire',
			'Voir les relances à faire'
		]
	},
	salesmate: {
		tags: ['Contacts', 'Affaires', 'Activités'],
		actions: ['Retrouver un contact', 'Mettre à jour une affaire', 'Ajouter une activité de suivi']
	},
	nethunt_crm: {
		tags: ['Gmail', 'Contacts', 'Affaires'],
		actions: [
			'Retrouver un client depuis vos e-mails',
			'Créer une affaire',
			'Ajouter une note de suivi'
		]
	},
	highlevel: {
		tags: ['Contacts', 'Campagnes', 'Rendez-vous'],
		actions: ['Retrouver un contact', 'Déclencher une campagne', 'Voir les rendez-vous pris']
	},
	follow_up_boss: {
		tags: ['Contacts', 'Biens', 'Relances'],
		actions: [
			'Retrouver un acquéreur et son historique',
			'Ajouter une note après une visite',
			'Programmer une relance'
		]
	},
	forcemanager: {
		tags: ['Visites', 'Clients', 'Ventes'],
		actions: ['Consigner une visite client', 'Retrouver un compte', 'Faire avancer une vente']
	},
	firmao: {
		tags: ['Clients', 'Devis', 'Factures'],
		actions: ['Retrouver un client', 'Créer un devis', 'Suivre une facture']
	},
	dynamics365: {
		tags: ['Comptes', 'Opportunités', 'Notes'],
		actions: [
			'Retrouver un compte et ses échanges',
			'Créer ou mettre à jour une opportunité',
			'Consigner un compte rendu'
		]
	},
	netsuite: {
		tags: ['Clients', 'Commandes', 'Factures'],
		actions: ['Retrouver un client', 'Consulter une commande', 'Suivre une facture']
	},
	odoo: {
		tags: ['Clients', 'Devis', 'Stocks'],
		actions: ['Retrouver un client ou un article', 'Créer un devis', 'Consulter les stocks']
	},
	apollo: {
		tags: ['Prospects', 'Entreprises', 'Listes'],
		actions: [
			'Trouver des prospects selon vos critères',
			'Récupérer leurs coordonnées',
			'Constituer une liste de démarchage'
		]
	},
	lusha: {
		tags: ['Coordonnées', 'Prospects', 'Entreprises'],
		actions: [
			'Trouver le contact d’un décideur',
			'Vérifier une adresse ou un numéro',
			'Enrichir une fiche client'
		]
	},
	zoominfo: {
		tags: ['Entreprises', 'Contacts', 'Données'],
		actions: [
			'Retrouver les informations d’une entreprise',
			'Identifier les bons interlocuteurs',
			'Enrichir votre base clients'
		]
	},
	gong: {
		tags: ['Appels', 'Analyse', 'Résumer'],
		actions: [
			'Récupérer le compte rendu d’un appel',
			'Repérer ce qui a fait basculer une vente',
			'Suivre les sujets abordés par vos clients'
		]
	},
	rocket_reach: {
		tags: ['Coordonnées', 'Profils', 'Entreprises'],
		actions: [
			'Trouver l’e-mail d’un professionnel',
			'Retrouver son entreprise et son poste',
			'Compléter une fiche contact'
		]
	},
	hunter: {
		tags: ['E-mails', 'Vérifier', 'Entreprises'],
		actions: [
			'Trouver les adresses d’une entreprise',
			'Vérifier qu’une adresse existe',
			'Deviner l’adresse d’une personne'
		]
	},

	// ── Projets & tâches ─────────────────────────────────────
	asana: {
		tags: ['Tâches', 'Projets', 'Suivi'],
		actions: [
			'Créer une tâche et l’assigner',
			'Voir où en est un projet',
			'Lister ce qui est en retard'
		]
	},
	trello: {
		tags: ['Cartes', 'Tableaux', 'Suivi'],
		actions: [
			'Créer une carte dans une liste',
			'Déplacer une carte d’une colonne à l’autre',
			'Résumer l’état d’un tableau'
		]
	},
	monday: {
		tags: ['Tâches', 'Tableaux', 'Suivi'],
		actions: [
			'Ajouter un élément à un tableau',
			'Mettre à jour un statut',
			'Voir où en est un projet'
		]
	},
	clickup: {
		tags: ['Tâches', 'Projets', 'Suivi'],
		actions: [
			'Créer une tâche et l’assigner',
			'Changer son statut',
			'Lister les tâches d’un projet'
		]
	},
	jira: {
		tags: ['Tickets', 'Sprints', 'Suivi'],
		actions: [
			'Créer un ticket',
			'Le faire avancer dans le flux',
			'Lister ce qui reste sur un sprint'
		]
	},
	confluence: {
		tags: ['Rechercher', 'Rédiger', 'Pages'],
		actions: [
			'Retrouver une page par son contenu',
			'Rédiger ou compléter une page',
			'Résumer un espace documentaire'
		]
	},
	basecamp: {
		tags: ['Tâches', 'Messages', 'Projets'],
		actions: [
			'Créer une tâche dans un projet',
			'Publier un message à l’équipe',
			'Voir ce qui a bougé cette semaine'
		]
	},
	wrike: {
		tags: ['Tâches', 'Projets', 'Suivi'],
		actions: [
			'Créer une tâche et l’assigner',
			'Suivre l’avancement d’un projet',
			'Lister les échéances proches'
		]
	},
	shortcut: {
		tags: ['Tickets', 'Itérations', 'Suivi'],
		actions: ['Créer un ticket', 'Le faire avancer', 'Voir ce qui reste sur l’itération']
	},
	linear: {
		tags: ['Tickets', 'Cycles', 'Suivi'],
		actions: [
			'Créer un ticket',
			'Changer son statut ou son responsable',
			'Lister ce qui reste sur le cycle'
		]
	},
	teamcamp: {
		tags: ['Tâches', 'Projets', 'Temps'],
		actions: ['Créer une tâche', 'Suivre l’avancement d’un projet', 'Consulter le temps passé']
	},
	kanbanize: {
		tags: ['Cartes', 'Flux', 'Suivi'],
		actions: ['Créer une carte', 'La déplacer dans le flux', 'Voir où ça bloque']
	},
	productboard: {
		tags: ['Retours', 'Fonctions', 'Feuille de route'],
		actions: [
			'Consigner un retour client',
			'Le rattacher à une fonctionnalité',
			'Consulter la feuille de route'
		]
	},
	miro: {
		tags: ['Tableaux', 'Notes', 'Partager'],
		actions: [
			'Retrouver un tableau',
			'Ajouter des notes à un atelier',
			'Récupérer le contenu d’un tableau'
		]
	},
	mural: {
		tags: ['Tableaux', 'Notes', 'Partager'],
		actions: ['Retrouver un tableau', 'Ajouter des notes', 'Récupérer le contenu d’un atelier']
	},
	baserow: {
		tags: ['Lire', 'Ajouter', 'Filtrer'],
		actions: [
			'Répondre à une question sur une base',
			'Ajouter une ligne',
			'Filtrer des enregistrements'
		]
	},
	nocodb: {
		tags: ['Lire', 'Ajouter', 'Filtrer'],
		actions: ['Interroger une table', 'Ajouter une ligne', 'Mettre à jour un enregistrement']
	},
	grist: {
		tags: ['Lire', 'Ajouter', 'Calculer'],
		actions: ['Interroger un tableau', 'Ajouter des lignes', 'Faire un récapitulatif']
	},
	ninox: {
		tags: ['Lire', 'Ajouter', 'Filtrer'],
		actions: ['Interroger une base', 'Ajouter un enregistrement', 'Mettre à jour une fiche']
	},
	fibery: {
		tags: ['Rechercher', 'Créer', 'Suivi'],
		actions: ['Retrouver une entité', 'Créer une tâche ou un document', 'Suivre l’avancement']
	},

	// ── Support client ───────────────────────────────────────
	zendesk: {
		tags: ['Tickets', 'Répondre', 'Suivi'],
		actions: [
			'Retrouver le ticket d’un client',
			'Rédiger une réponse',
			'Lister ce qui attend depuis trop longtemps'
		]
	},
	intercom: {
		tags: ['Conversations', 'Répondre', 'Contacts'],
		actions: [
			'Retrouver une conversation client',
			'Répondre à un message',
			'Consulter la fiche d’un utilisateur'
		]
	},
	freshdesk: {
		tags: ['Tickets', 'Répondre', 'Suivi'],
		actions: ['Retrouver un ticket', 'Y répondre ou le clôturer', 'Lister les tickets en attente']
	},
	freshservice: {
		tags: ['Demandes', 'Incidents', 'Suivi'],
		actions: ['Créer une demande interne', 'Suivre un incident', 'Lister ce qui est en attente']
	},
	help_scout: {
		tags: ['Conversations', 'Répondre', 'Suivi'],
		actions: [
			'Retrouver une conversation',
			'Rédiger une réponse',
			'Voir ce qui n’a pas encore été traité'
		]
	},
	helpdesk: {
		tags: ['Tickets', 'Répondre', 'Suivi'],
		actions: ['Retrouver un ticket', 'Y répondre', 'Suivre les tickets ouverts']
	},
	gorgias: {
		tags: ['Tickets', 'Commandes', 'Répondre'],
		actions: ['Retrouver la demande d’un client', 'Voir sa commande liée', 'Rédiger une réponse']
	},
	re_amaze: {
		tags: ['Conversations', 'Répondre', 'Suivi'],
		actions: ['Retrouver une conversation', 'Y répondre', 'Lister ce qui attend']
	},
	supportbee: {
		tags: ['Tickets', 'Répondre', 'Attribuer'],
		actions: ['Retrouver un ticket', 'Y répondre', 'L’attribuer à quelqu’un']
	},
	plain: {
		tags: ['Conversations', 'Clients', 'Répondre'],
		actions: ['Retrouver la conversation d’un client', 'Y répondre', 'Consulter son historique']
	},
	canny: {
		tags: ['Retours', 'Votes', 'Feuille de route'],
		actions: [
			'Consigner une demande client',
			'Voir ce qui est le plus demandé',
			'Suivre l’avancement d’une idée'
		]
	},
	gleap: {
		tags: ['Bugs', 'Retours', 'Suivi'],
		actions: [
			'Récupérer un rapport de bug',
			'Suivre les retours utilisateurs',
			'Rattacher un retour à un ticket'
		]
	},
	servicenow: {
		tags: ['Demandes', 'Incidents', 'Suivi'],
		actions: ['Créer une demande', 'Suivre un incident', 'Consulter l’état d’un dossier']
	},

	// ── Compta & paiement ────────────────────────────────────
	stripe: {
		tags: ['Paiements', 'Clients', 'Factures'],
		actions: [
			'Retrouver un paiement ou un client',
			'Consulter les encaissements du mois',
			'Suivre un abonnement ou un remboursement'
		]
	},
	paypal: {
		tags: ['Paiements', 'Clients', 'Suivi'],
		actions: ['Retrouver une transaction', 'Consulter le solde', 'Suivre un remboursement']
	},
	quickbooks: {
		tags: ['Factures', 'Clients', 'Dépenses'],
		actions: ['Créer une facture', 'Retrouver ce qu’un client doit', 'Consigner une dépense']
	},
	xero: {
		tags: ['Factures', 'Clients', 'Dépenses'],
		actions: ['Créer une facture', 'Suivre les impayés', 'Enregistrer une dépense']
	},
	freshbooks: {
		tags: ['Factures', 'Devis', 'Temps'],
		actions: [
			'Créer une facture ou un devis',
			'Suivre les paiements reçus',
			'Facturer du temps passé'
		]
	},
	freeagent: {
		tags: ['Factures', 'Dépenses', 'Suivi'],
		actions: ['Créer une facture', 'Enregistrer une dépense', 'Consulter les impayés']
	},
	moneybird: {
		tags: ['Factures', 'Clients', 'Suivi'],
		actions: ['Créer une facture', 'Retrouver un client', 'Suivre les règlements']
	},
	sevdesk: {
		tags: ['Factures', 'Dépenses', 'Clients'],
		actions: ['Créer une facture', 'Enregistrer un justificatif', 'Suivre les impayés']
	},
	lexoffice: {
		tags: ['Factures', 'Dépenses', 'Clients'],
		actions: ['Créer une facture', 'Enregistrer une dépense', 'Retrouver un client']
	},
	elorus: {
		tags: ['Factures', 'Devis', 'Temps'],
		actions: ['Créer une facture ou un devis', 'Suivre les paiements', 'Facturer du temps passé']
	},
	quaderno: {
		tags: ['TVA', 'Factures', 'Suivi'],
		actions: ['Éditer une facture conforme', 'Suivre la TVA collectée', 'Retrouver un justificatif']
	},
	square: {
		tags: ['Encaissements', 'Clients', 'Articles'],
		actions: [
			'Consulter les ventes du jour',
			'Retrouver une transaction',
			'Mettre à jour un article'
		]
	},
	razorpay: {
		tags: ['Paiements', 'Clients', 'Remboursements'],
		actions: ['Retrouver un paiement', 'Suivre les encaissements', 'Lancer un remboursement']
	},
	paystack: {
		tags: ['Paiements', 'Clients', 'Suivi'],
		actions: ['Retrouver une transaction', 'Suivre les encaissements', 'Consulter un client']
	},
	flutterwave: {
		tags: ['Paiements', 'Clients', 'Suivi'],
		actions: ['Retrouver un paiement', 'Suivre les encaissements', 'Lancer un remboursement']
	},
	lemon_squeezy: {
		tags: ['Ventes', 'Abonnements', 'Clients'],
		actions: ['Consulter les ventes du mois', 'Retrouver un client', 'Suivre un abonnement']
	},
	gumroad: {
		tags: ['Ventes', 'Produits', 'Clients'],
		actions: ['Consulter les ventes', 'Retrouver un acheteur', 'Mettre à jour un produit']
	},
	brex: {
		tags: ['Dépenses', 'Cartes', 'Suivi'],
		actions: [
			'Consulter les dépenses de l’équipe',
			'Retrouver une transaction',
			'Suivre le budget d’une carte'
		]
	},
	ramp: {
		tags: ['Dépenses', 'Notes de frais', 'Cartes'],
		actions: ['Consulter les dépenses', 'Suivre une note de frais', 'Retrouver un justificatif']
	},
	ynab: {
		tags: ['Budget', 'Comptes', 'Suivi'],
		actions: ['Consulter votre budget', 'Voir ce qu’il reste sur un poste', 'Retrouver une dépense']
	},
	taxjar: {
		tags: ['Taxes', 'Ventes', 'Déclarations'],
		actions: [
			'Calculer la taxe d’une vente',
			'Suivre la taxe collectée',
			'Préparer une déclaration'
		]
	},
	zoho_books: {
		tags: ['Factures', 'Clients', 'Dépenses'],
		actions: ['Créer une facture', 'Suivre les impayés', 'Enregistrer une dépense']
	},
	zoho_invoice: {
		tags: ['Factures', 'Devis', 'Clients'],
		actions: ['Créer une facture ou un devis', 'Relancer un impayé', 'Retrouver un client']
	},
	zoho_inventory: {
		tags: ['Stocks', 'Commandes', 'Articles'],
		actions: [
			'Consulter le stock d’un article',
			'Suivre une commande',
			'Mettre à jour une quantité'
		]
	},

	// ── Marketing & e-mailing ────────────────────────────────
	mailchimp: {
		tags: ['Campagnes', 'Contacts', 'Statistiques'],
		actions: [
			'Rédiger et programmer une campagne',
			'Ajouter un contact à une liste',
			'Consulter les ouvertures et les clics'
		]
	},
	brevo: {
		tags: ['Campagnes', 'Contacts', 'Statistiques'],
		actions: [
			'Préparer un envoi à une liste',
			'Ajouter ou mettre à jour un contact',
			'Consulter les résultats d’une campagne'
		]
	},
	sendgrid: {
		tags: ['Envois', 'Modèles', 'Suivi'],
		actions: [
			'Envoyer un e-mail depuis un modèle',
			'Suivre les envois et les rebonds',
			'Gérer vos listes de destinataires'
		]
	},
	mailerlite: {
		tags: ['Campagnes', 'Contacts', 'Statistiques'],
		actions: ['Préparer une campagne', 'Ajouter un abonné', 'Consulter les résultats']
	},
	mailersend: {
		tags: ['Envois', 'Modèles', 'Suivi'],
		actions: [
			'Envoyer un e-mail transactionnel',
			'Suivre la remise et les rebonds',
			'Gérer vos modèles'
		]
	},
	klaviyo: {
		tags: ['Campagnes', 'Segments', 'Statistiques'],
		actions: [
			'Créer un segment de clients',
			'Déclencher une campagne',
			'Consulter le chiffre généré'
		]
	},
	active_campaign: {
		tags: ['Scénarios', 'Contacts', 'Campagnes'],
		actions: ['Ajouter un contact à un scénario', 'Envoyer une campagne', 'Suivre les résultats']
	},
	constant_contact: {
		tags: ['Campagnes', 'Contacts', 'Statistiques'],
		actions: ['Préparer une campagne', 'Gérer vos listes', 'Consulter les ouvertures']
	},
	omnisend: {
		tags: ['Campagnes', 'Boutique', 'Segments'],
		actions: [
			'Envoyer une campagne à vos clients',
			'Créer un segment',
			'Suivre les ventes générées'
		]
	},
	moosend: {
		tags: ['Campagnes', 'Contacts', 'Statistiques'],
		actions: ['Préparer une campagne', 'Ajouter un abonné', 'Consulter les résultats']
	},
	sender: {
		tags: ['Campagnes', 'Contacts', 'Suivi'],
		actions: ['Envoyer une campagne', 'Gérer vos abonnés', 'Consulter les statistiques']
	},
	emailoctopus: {
		tags: ['Campagnes', 'Abonnés', 'Suivi'],
		actions: ['Préparer un envoi', 'Ajouter un abonné', 'Consulter les résultats']
	},
	loops_so: {
		tags: ['Envois', 'Contacts', 'Scénarios'],
		actions: ['Envoyer un e-mail produit', 'Ajouter un contact', 'Déclencher un scénario']
	},
	customerio: {
		tags: ['Scénarios', 'Contacts', 'Envois'],
		actions: [
			'Déclencher un message automatisé',
			'Mettre à jour un contact',
			'Suivre un parcours client'
		]
	},
	iterable: {
		tags: ['Campagnes', 'Contacts', 'Parcours'],
		actions: ['Envoyer une campagne', 'Ajouter un contact à un parcours', 'Consulter les résultats']
	},
	postmark: {
		tags: ['Envois', 'Modèles', 'Suivi'],
		actions: ['Envoyer un e-mail transactionnel', 'Suivre la remise', 'Consulter les rebonds']
	},
	resend: {
		tags: ['Envois', 'Modèles', 'Suivi'],
		actions: ['Envoyer un e-mail', 'Utiliser un modèle', 'Suivre la remise']
	},
	mailtrap: {
		tags: ['Envois', 'Tests', 'Suivi'],
		actions: [
			'Tester un e-mail avant envoi',
			'Envoyer un message transactionnel',
			'Consulter les rebonds'
		]
	},
	kit: {
		tags: ['Newsletter', 'Abonnés', 'Séquences'],
		actions: ['Envoyer une newsletter', 'Ajouter un abonné', 'Déclencher une séquence']
	},
	instantly: {
		tags: ['Prospection', 'Séquences', 'Réponses'],
		actions: ['Lancer une campagne de prospection', 'Ajouter des prospects', 'Suivre les réponses']
	},
	lemlist: {
		tags: ['Prospection', 'Séquences', 'Réponses'],
		actions: [
			'Lancer une séquence de prospection',
			'Ajouter des prospects',
			'Suivre les réponses obtenues'
		]
	},
	reply_io: {
		tags: ['Prospection', 'Séquences', 'Réponses'],
		actions: ['Lancer une séquence', 'Ajouter un prospect', 'Suivre les réponses']
	},
	woodpecker_co: {
		tags: ['Relances', 'Séquences', 'Réponses'],
		actions: ['Programmer une relance', 'Ajouter un prospect', 'Suivre les réponses']
	},
	ayrshare: {
		tags: ['Publier', 'Réseaux', 'Statistiques'],
		actions: [
			'Publier sur plusieurs réseaux d’un coup',
			'Programmer une publication',
			'Consulter les statistiques'
		]
	},
	postiz_mcp: {
		tags: ['Publier', 'Programmer', 'Réseaux'],
		actions: [
			'Programmer une publication',
			'Publier sur plusieurs réseaux',
			'Suivre le calendrier éditorial'
		]
	},
	typefully: {
		tags: ['Rédiger', 'Programmer', 'Publier'],
		actions: ['Rédiger un fil ou un post', 'Le programmer à l’avance', 'Suivre ses résultats']
	},
	planly: {
		tags: ['Programmer', 'Réseaux', 'Calendrier'],
		actions: [
			'Programmer une publication',
			'Voir le calendrier de la semaine',
			'Publier sur plusieurs comptes'
		]
	},
	metaads: {
		tags: ['Publicités', 'Budget', 'Résultats'],
		actions: [
			'Consulter les performances d’une campagne',
			'Suivre le budget dépensé',
			'Mettre une campagne en pause'
		]
	},
	linkedin_ads: {
		tags: ['Publicités', 'Budget', 'Résultats'],
		actions: [
			'Consulter les performances d’une campagne',
			'Suivre le budget',
			'Comparer vos annonces'
		]
	},
	googleads: {
		tags: ['Publicités', 'Budget', 'Résultats'],
		actions: [
			'Consulter les performances d’une campagne',
			'Suivre le coût par clic',
			'Mettre une annonce en pause'
		]
	},

	// ── Réseaux sociaux ──────────────────────────────────────
	reddit: {
		tags: ['Publier', 'Commenter', 'Rechercher'],
		actions: [
			'Publier dans un subreddit',
			'Répondre à un commentaire',
			'Chercher ce qui se dit sur un sujet'
		]
	},
	snapchat: {
		tags: ['Publier', 'Compte', 'Statistiques'],
		actions: ['Publier un contenu', 'Consulter votre compte', 'Suivre les statistiques']
	},

	// ── RH & temps ───────────────────────────────────────────
	bamboohr: {
		tags: ['Salariés', 'Congés', 'Dossiers'],
		actions: [
			'Retrouver la fiche d’un salarié',
			'Consulter les congés posés',
			'Suivre une demande d’absence'
		]
	},
	gusto: {
		tags: ['Paie', 'Salariés', 'Congés'],
		actions: [
			'Consulter la fiche d’un salarié',
			'Suivre un cycle de paie',
			'Voir les congés en cours'
		]
	},
	workday: {
		tags: ['Salariés', 'Paie', 'Congés'],
		actions: ['Retrouver un collaborateur', 'Consulter ses congés', 'Suivre une demande RH']
	},
	sap_successfactors: {
		tags: ['Salariés', 'Carrières', 'Congés'],
		actions: ['Retrouver un collaborateur', 'Consulter son parcours', 'Suivre une demande']
	},
	greenhouse: {
		tags: ['Candidats', 'Offres', 'Entretiens'],
		actions: ['Retrouver un candidat', 'Suivre où il en est', 'Consulter les offres ouvertes']
	},
	lever: {
		tags: ['Candidats', 'Offres', 'Entretiens'],
		actions: [
			'Retrouver un candidat',
			'Faire avancer sa candidature',
			'Consulter les postes ouverts'
		]
	},
	ashby: {
		tags: ['Candidats', 'Offres', 'Entretiens'],
		actions: ['Retrouver un candidat', 'Suivre son avancement', 'Consulter le vivier']
	},
	recruitee: {
		tags: ['Candidats', 'Offres', 'Suivi'],
		actions: [
			'Retrouver un candidat',
			'Faire avancer sa candidature',
			'Publier ou suivre une offre'
		]
	},
	workable: {
		tags: ['Candidats', 'Offres', 'Suivi'],
		actions: ['Retrouver un candidat', 'Suivre son avancement', 'Consulter les offres']
	},
	breezy_hr: {
		tags: ['Candidats', 'Offres', 'Suivi'],
		actions: ['Retrouver un candidat', 'Faire avancer sa candidature', 'Consulter les postes']
	},
	breathehr: {
		tags: ['Salariés', 'Congés', 'Dossiers'],
		actions: ['Retrouver un salarié', 'Consulter les absences', 'Suivre une demande']
	},
	talenthr: {
		tags: ['Salariés', 'Congés', 'Dossiers'],
		actions: ['Retrouver un salarié', 'Consulter ses congés', 'Suivre une demande']
	},
	connecteam: {
		tags: ['Équipes', 'Plannings', 'Pointage'],
		actions: [
			'Consulter le planning du jour',
			'Suivre les heures pointées',
			'Envoyer un message à l’équipe'
		]
	},
	timecamp: {
		tags: ['Temps', 'Projets', 'Rapports'],
		actions: [
			'Consulter le temps passé sur un projet',
			'Démarrer ou arrêter un suivi',
			'Sortir un récapitulatif'
		]
	},
	clockify: {
		tags: ['Temps', 'Projets', 'Rapports'],
		actions: ['Consulter le temps passé', 'Enregistrer une durée', 'Sortir un récapitulatif']
	},
	toggl: {
		tags: ['Temps', 'Projets', 'Rapports'],
		actions: [
			'Démarrer ou arrêter un suivi',
			'Consulter le temps par projet',
			'Sortir un récapitulatif'
		]
	},
	harvest: {
		tags: ['Temps', 'Factures', 'Projets'],
		actions: [
			'Enregistrer du temps sur un projet',
			'Facturer les heures passées',
			'Consulter un récapitulatif'
		]
	},
	everhour: {
		tags: ['Temps', 'Projets', 'Budget'],
		actions: ['Enregistrer du temps', 'Suivre le budget d’un projet', 'Sortir un rapport']
	},
	timely: {
		tags: ['Temps', 'Projets', 'Rapports'],
		actions: [
			'Consulter votre journée',
			'Rattacher du temps à un projet',
			'Sortir un récapitulatif'
		]
	},

	// ── Signature & devis ────────────────────────────────────
	docusign: {
		tags: ['Signer', 'Envoyer', 'Suivre'],
		actions: [
			'Envoyer un document à signer',
			'Savoir qui a signé et qui traîne',
			'Récupérer le document signé'
		]
	},
	dropbox_sign: {
		tags: ['Signer', 'Envoyer', 'Suivre'],
		actions: [
			'Envoyer un document à signer',
			'Relancer un signataire',
			'Récupérer le document signé'
		]
	},
	pandadoc: {
		tags: ['Devis', 'Signer', 'Suivre'],
		actions: ['Créer un devis depuis un modèle', 'L’envoyer à signer', 'Savoir s’il a été ouvert']
	},
	documenso: {
		tags: ['Signer', 'Envoyer', 'Suivre'],
		actions: [
			'Envoyer un document à signer',
			'Suivre les signatures',
			'Récupérer le document final'
		]
	},
	docuseal: {
		tags: ['Signer', 'Modèles', 'Suivre'],
		actions: ['Envoyer un document à signer', 'Utiliser un modèle', 'Suivre les signatures']
	},
	signwell: {
		tags: ['Signer', 'Envoyer', 'Suivre'],
		actions: [
			'Envoyer un document à signer',
			'Relancer un signataire',
			'Récupérer le document signé'
		]
	},
	signaturely: {
		tags: ['Signer', 'Envoyer', 'Suivre'],
		actions: ['Envoyer un document à signer', 'Suivre l’avancement', 'Récupérer le document']
	},
	eversign: {
		tags: ['Signer', 'Envoyer', 'Suivre'],
		actions: [
			'Envoyer un document à signer',
			'Suivre les signatures',
			'Télécharger le document signé'
		]
	},
	esignatures_io: {
		tags: ['Contrats', 'Signer', 'Suivre'],
		actions: ['Envoyer un contrat à signer', 'Suivre son avancement', 'Récupérer le contrat signé']
	},
	boldsign: {
		tags: ['Signer', 'Modèles', 'Suivre'],
		actions: ['Envoyer un document à signer', 'Partir d’un modèle', 'Suivre les signatures']
	},
	better_proposals: {
		tags: ['Propositions', 'Signer', 'Suivre'],
		actions: [
			'Créer une proposition commerciale',
			'L’envoyer au client',
			'Savoir si elle a été ouverte'
		]
	},

	// ── Vente en ligne & livraison ───────────────────────────
	shopify: {
		tags: ['Commandes', 'Produits', 'Clients'],
		actions: [
			'Retrouver une commande',
			'Consulter le stock d’un produit',
			'Voir les ventes du jour'
		]
	},
	wix: {
		tags: ['Site', 'Commandes', 'Contacts'],
		actions: ['Consulter les commandes', 'Retrouver un contact', 'Mettre à jour une page']
	},
	webflow: {
		tags: ['Site', 'Contenu', 'Publier'],
		actions: ['Mettre à jour un contenu', 'Ajouter un article', 'Publier le site']
	},
	loyverse: {
		tags: ['Ventes', 'Stocks', 'Clients'],
		actions: ['Consulter les ventes du jour', 'Vérifier un stock', 'Retrouver un client']
	},
	baselinker: {
		tags: ['Commandes', 'Stocks', 'Expéditions'],
		actions: ['Retrouver une commande', 'Suivre les stocks', 'Préparer une expédition']
	},
	cloudcart: {
		tags: ['Commandes', 'Produits', 'Clients'],
		actions: ['Retrouver une commande', 'Mettre à jour un produit', 'Consulter les ventes']
	},
	shippo: {
		tags: ['Expéditions', 'Étiquettes', 'Suivi'],
		actions: [
			'Créer une étiquette d’expédition',
			'Comparer les tarifs transporteurs',
			'Suivre un colis'
		]
	},
	shipengine: {
		tags: ['Expéditions', 'Étiquettes', 'Suivi'],
		actions: ['Créer une étiquette', 'Comparer les tarifs', 'Suivre un colis']
	},
	shipday: {
		tags: ['Livraisons', 'Livreurs', 'Suivi'],
		actions: ['Créer une livraison', 'L’attribuer à un livreur', 'Suivre son avancement']
	},
	detrack: {
		tags: ['Livraisons', 'Preuves', 'Suivi'],
		actions: [
			'Suivre une livraison en cours',
			'Récupérer la preuve de livraison',
			'Consulter la tournée du jour'
		]
	},
	route4me: {
		tags: ['Tournées', 'Itinéraires', 'Suivi'],
		actions: ['Créer une tournée', 'Optimiser l’ordre des arrêts', 'Suivre son avancement']
	},
	optimoroute: {
		tags: ['Tournées', 'Itinéraires', 'Suivi'],
		actions: ['Planifier une tournée', 'Optimiser les trajets', 'Suivre les livraisons']
	},
	payhip: {
		tags: ['Ventes', 'Produits', 'Clients'],
		actions: ['Consulter les ventes', 'Retrouver un acheteur', 'Mettre à jour un produit']
	},
	whop: {
		tags: ['Abonnements', 'Ventes', 'Membres'],
		actions: ['Consulter les ventes', 'Suivre un abonnement', 'Retrouver un membre']
	},

	// ── Formulaires & enquêtes ───────────────────────────────
	typeform: {
		tags: ['Réponses', 'Formulaires', 'Résumer'],
		actions: [
			'Récupérer les réponses d’un formulaire',
			'Résumer ce qui ressort',
			'Suivre le nombre de réponses'
		]
	},
	jotform: {
		tags: ['Réponses', 'Formulaires', 'Résumer'],
		actions: ['Récupérer les réponses', 'Résumer les retours', 'Suivre les envois']
	},
	tally: {
		tags: ['Réponses', 'Formulaires', 'Résumer'],
		actions: ['Récupérer les réponses', 'Résumer ce qui ressort', 'Suivre les soumissions']
	},
	fillout_forms: {
		tags: ['Réponses', 'Formulaires', 'Suivi'],
		actions: ['Récupérer les réponses', 'Suivre les soumissions', 'Résumer les retours']
	},
	formbricks: {
		tags: ['Enquêtes', 'Réponses', 'Résumer'],
		actions: [
			'Récupérer les réponses d’une enquête',
			'Résumer les retours',
			'Suivre la participation'
		]
	},
	getform: {
		tags: ['Réponses', 'Formulaires', 'Suivi'],
		actions: ['Récupérer les soumissions', 'Suivre les nouveaux envois', 'Résumer les retours']
	},
	formsite: {
		tags: ['Réponses', 'Formulaires', 'Suivi'],
		actions: ['Récupérer les réponses', 'Suivre les soumissions', 'Sortir un récapitulatif']
	},
	paperform: {
		tags: ['Réponses', 'Formulaires', 'Suivi'],
		actions: ['Récupérer les réponses', 'Suivre les soumissions', 'Résumer les retours']
	},
	survey_monkey: {
		tags: ['Enquêtes', 'Réponses', 'Résumer'],
		actions: [
			'Récupérer les réponses d’une enquête',
			'Résumer ce qui ressort',
			'Suivre la participation'
		]
	},
	googleforms: {
		tags: ['Réponses', 'Formulaires', 'Résumer'],
		actions: ['Récupérer les réponses', 'Résumer les retours', 'Suivre le nombre de réponses']
	},
	delighted: {
		tags: ['Satisfaction', 'Retours', 'Suivi'],
		actions: [
			'Consulter le score de satisfaction',
			'Lire les retours clients',
			'Repérer les mécontents'
		]
	},
	satismeter: {
		tags: ['Satisfaction', 'Retours', 'Suivi'],
		actions: ['Consulter le score de satisfaction', 'Lire les commentaires', 'Suivre l’évolution']
	},
	refiner: {
		tags: ['Enquêtes', 'Retours', 'Segments'],
		actions: ['Récupérer les réponses', 'Cibler un segment de clients', 'Résumer les retours']
	},
	simplesat: {
		tags: ['Satisfaction', 'Support', 'Retours'],
		actions: [
			'Consulter la satisfaction après support',
			'Lire les commentaires',
			'Repérer les dossiers ratés'
		]
	},
	retently: {
		tags: ['Satisfaction', 'Retours', 'Suivi'],
		actions: [
			'Consulter votre score de recommandation',
			'Lire les retours clients',
			'Suivre l’évolution'
		]
	},

	// ── Analyse & données ────────────────────────────────────
	google_analytics: {
		tags: ['Visites', 'Sources', 'Rapports'],
		actions: [
			'Consulter la fréquentation du site',
			'Savoir d’où viennent les visiteurs',
			'Comparer deux périodes'
		]
	},
	microsoft_power_bi: {
		tags: ['Tableaux de bord', 'Rapports', 'Données'],
		actions: ['Consulter un tableau de bord', 'Récupérer un indicateur', 'Rafraîchir un rapport']
	},
	metabase: {
		tags: ['Requêtes', 'Tableaux de bord', 'Données'],
		actions: [
			'Lancer une requête existante',
			'Consulter un tableau de bord',
			'Récupérer un chiffre précis'
		]
	},
	mixpanel: {
		tags: ['Usage', 'Entonnoirs', 'Rapports'],
		actions: [
			'Consulter l’usage de votre produit',
			'Suivre un entonnoir de conversion',
			'Comparer deux périodes'
		]
	},
	amplitude: {
		tags: ['Usage', 'Entonnoirs', 'Rapports'],
		actions: ['Consulter l’usage du produit', 'Suivre une conversion', 'Comparer des cohortes']
	},
	posthog: {
		tags: ['Usage', 'Entonnoirs', 'Sessions'],
		actions: ['Consulter l’usage du produit', 'Suivre un entonnoir', 'Retrouver une session']
	},
	plausible_analytics: {
		tags: ['Visites', 'Sources', 'Rapports'],
		actions: [
			'Consulter la fréquentation',
			'Savoir d’où viennent les visiteurs',
			'Comparer deux périodes'
		]
	},
	simple_analytics: {
		tags: ['Visites', 'Sources', 'Rapports'],
		actions: [
			'Consulter la fréquentation',
			'Voir les pages les plus vues',
			'Comparer deux périodes'
		]
	},
	databox: {
		tags: ['Indicateurs', 'Tableaux de bord', 'Suivi'],
		actions: ['Consulter un indicateur', 'Suivre un objectif', 'Comparer deux périodes']
	},
	klipfolio: {
		tags: ['Indicateurs', 'Tableaux de bord', 'Suivi'],
		actions: ['Consulter un tableau de bord', 'Récupérer un indicateur', 'Suivre un objectif']
	},
	google_search_console: {
		tags: ['Recherche', 'Positions', 'Pages'],
		actions: [
			'Voir sur quels mots vous ressortez',
			'Suivre vos positions',
			'Repérer les pages en baisse'
		]
	},
	semrush: {
		tags: ['Mots-clés', 'Concurrents', 'Positions'],
		actions: [
			'Analyser les mots-clés d’un site',
			'Comparer avec un concurrent',
			'Suivre vos positions'
		]
	},
	ahrefs: {
		tags: ['Mots-clés', 'Liens', 'Concurrents'],
		actions: [
			'Analyser les mots-clés d’un site',
			'Consulter les liens entrants',
			'Comparer avec un concurrent'
		]
	},
	moz: {
		tags: ['Mots-clés', 'Autorité', 'Liens'],
		actions: [
			'Consulter l’autorité d’un domaine',
			'Analyser des mots-clés',
			'Suivre les liens entrants'
		]
	},

	// ── Automatisation ───────────────────────────────────────
	make: {
		tags: ['Scénarios', 'Déclencher', 'Suivi'],
		actions: ['Déclencher un scénario', 'Consulter les exécutions', 'Repérer un scénario en échec']
	},
	bubble: {
		tags: ['Données', 'Application', 'Flux'],
		actions: [
			'Lire ou modifier des données',
			'Déclencher un flux',
			'Consulter l’état de l’application'
		]
	},
	softr: {
		tags: ['Utilisateurs', 'Données', 'Application'],
		actions: ['Consulter les utilisateurs', 'Lire ou modifier des données', 'Suivre l’activité']
	},
	nango: {
		tags: ['Connexions', 'Synchros', 'Suivi'],
		actions: [
			'Consulter les connexions établies',
			'Relancer une synchronisation',
			'Repérer une connexion cassée'
		]
	},
	celigo: {
		tags: ['Flux', 'Synchros', 'Suivi'],
		actions: [
			'Déclencher un flux entre logiciels',
			'Consulter les exécutions',
			'Repérer une erreur'
		]
	},

	// ── Recherche & extraction web ───────────────────────────
	exa: {
		tags: ['Rechercher', 'Sources', 'Contenu'],
		actions: [
			'Chercher sur le web par le sens, pas par mots-clés',
			'Retrouver des pages proches d’une référence',
			'Récupérer le contenu des résultats'
		]
	},
	tavily: {
		tags: ['Rechercher', 'Sources', 'Résumer'],
		actions: [
			'Chercher une information sur le web',
			'Obtenir une réponse avec ses sources',
			'Récupérer le contenu d’une page'
		]
	},
	firecrawl: {
		tags: ['Extraire', 'Site entier', 'Texte'],
		actions: [
			'Transformer une page en texte propre',
			'Parcourir un site entier',
			'Extraire des données précises d’une page'
		]
	},
	perplexityai: {
		tags: ['Rechercher', 'Sources', 'Répondre'],
		actions: [
			'Poser une question et obtenir une réponse sourcée',
			'Vérifier une information récente',
			'Retrouver les sources citées'
		]
	},
	linkup: {
		tags: ['Rechercher', 'Sources', 'Répondre'],
		actions: [
			'Chercher une information à jour',
			'Obtenir une réponse avec ses sources',
			'Suivre l’actualité d’un sujet'
		]
	},
	openperplex: {
		tags: ['Rechercher', 'Sources', 'Répondre'],
		actions: [
			'Chercher sur le web',
			'Obtenir une réponse sourcée',
			'Récupérer le contenu d’une page'
		]
	},
	serpapi: {
		tags: ['Google', 'Résultats', 'Positions'],
		actions: [
			'Récupérer les résultats Google d’une requête',
			'Suivre la position d’un site',
			'Comparer les résultats par pays'
		]
	},
	brightdata: {
		tags: ['Extraire', 'Web', 'Données'],
		actions: [
			'Extraire des données d’un site',
			'Récupérer une page difficile d’accès',
			'Collecter à grande échelle'
		]
	},
	apify: {
		tags: ['Robots', 'Extraire', 'Programmer'],
		actions: [
			'Lancer un robot d’extraction',
			'Récupérer les données collectées',
			'Programmer une collecte régulière'
		]
	},
	browseai: {
		tags: ['Surveiller', 'Extraire', 'Alerter'],
		actions: [
			'Surveiller une page et ses changements',
			'Extraire un tableau ou une liste',
			'Être alerté quand ça bouge'
		]
	},
	browserbase_tool: {
		tags: ['Navigateur', 'Naviguer', 'Extraire'],
		actions: ['Ouvrir un site et y naviguer', 'Remplir un formulaire', 'Récupérer ce qui s’affiche']
	},
	hyperbrowser: {
		tags: ['Navigateur', 'Naviguer', 'Extraire'],
		actions: [
			'Piloter un navigateur',
			'Passer une page qui demande une connexion',
			'Récupérer le contenu affiché'
		]
	},
	scrapegraph_ai: {
		tags: ['Extraire', 'IA', 'Données'],
		actions: [
			'Décrire ce qu’on veut, obtenir les données',
			'Extraire d’une page sans écrire de règle',
			'Structurer un contenu web'
		]
	},
	diffbot: {
		tags: ['Extraire', 'Articles', 'Entreprises'],
		actions: [
			'Transformer un article en données',
			'Récupérer les informations d’une entreprise',
			'Extraire une fiche produit'
		]
	},
	agentql: {
		tags: ['Interroger', 'Pages', 'Données'],
		actions: [
			'Interroger une page comme une base',
			'Récupérer un champ précis',
			'Résister aux changements de mise en page'
		]
	},
	kadoa: {
		tags: ['Extraire', 'Surveiller', 'Données'],
		actions: [
			'Extraire les données d’un site',
			'Surveiller leur évolution',
			'Récupérer un flux structuré'
		]
	},
	news_api: {
		tags: ['Actualité', 'Presse', 'Rechercher'],
		actions: [
			'Chercher des articles sur un sujet',
			'Suivre ce qui se dit d’une entreprise',
			'Récupérer les titres du jour'
		]
	},
	composio_search: {
		tags: ['Rechercher', 'Web', 'Sources'],
		actions: [
			'Chercher une information sur le web',
			'Récupérer les résultats',
			'Consulter le contenu d’une page'
		]
	},

	// ── Mémoire & bases vectorielles ─────────────────────────
	mem0: {
		tags: ['Mémoire', 'Retenir', 'Rappeler'],
		actions: [
			'Retenir ce que vous dites d’une fois sur l’autre',
			'Rappeler vos préférences',
			'Oublier ce que vous demandez d’oublier'
		]
	},
	zep: {
		tags: ['Mémoire', 'Conversations', 'Rappeler'],
		actions: [
			'Garder le fil des conversations passées',
			'Retrouver un échange ancien',
			'Rappeler le contexte utile'
		]
	},
	pinecone: {
		tags: ['Documents', 'Rechercher', 'Indexer'],
		actions: [
			'Chercher dans vos documents par le sens',
			'Ajouter un document à l’index',
			'Retrouver les passages pertinents'
		]
	},
	ragie: {
		tags: ['Documents', 'Rechercher', 'Indexer'],
		actions: [
			'Interroger vos documents en langage courant',
			'Ajouter des fichiers à la base',
			'Récupérer les extraits utiles'
		]
	},
	needle: {
		tags: ['Documents', 'Rechercher', 'Indexer'],
		actions: ['Chercher dans vos documents', 'Ajouter des fichiers', 'Obtenir une réponse sourcée']
	},

	// ── Bac à sable de code ──────────────────────────────────
	e2b: {
		tags: ['Exécuter', 'Isolé', 'Fichiers'],
		actions: [
			'Exécuter du code sans risque pour la machine',
			'Analyser un fichier de données',
			'Récupérer le résultat produit'
		]
	},
	daytona: {
		tags: ['Environnements', 'Isolé', 'Exécuter'],
		actions: [
			'Ouvrir un environnement de travail isolé',
			'Y exécuter du code',
			'Récupérer les fichiers produits'
		]
	},

	// ── Développement & design ───────────────────────────────
	github: {
		tags: ['Dépôts', 'Tickets', 'Fusions'],
		actions: [
			'Retrouver un ticket ou une demande de fusion',
			'Créer un ticket',
			'Consulter l’activité d’un dépôt'
		]
	},
	gitlab: {
		tags: ['Dépôts', 'Tickets', 'Fusions'],
		actions: [
			'Retrouver un ticket',
			'Consulter une demande de fusion',
			'Suivre une chaîne de build'
		]
	},
	bitbucket: {
		tags: ['Dépôts', 'Tickets', 'Fusions'],
		actions: ['Consulter un dépôt', 'Retrouver une demande de fusion', 'Suivre les commits']
	},
	gitea: {
		tags: ['Dépôts', 'Tickets', 'Fusions'],
		actions: ['Consulter un dépôt', 'Créer un ticket', 'Suivre une demande de fusion']
	},
	sentry: {
		tags: ['Erreurs', 'Alertes', 'Suivi'],
		actions: [
			'Consulter les erreurs récentes',
			'Voir combien d’utilisateurs sont touchés',
			'Suivre une erreur jusqu’à sa correction'
		]
	},
	datadog: {
		tags: ['Surveillance', 'Alertes', 'Journaux'],
		actions: [
			'Consulter l’état de vos serveurs',
			'Voir les alertes en cours',
			'Chercher dans les journaux'
		]
	},
	new_relic: {
		tags: ['Surveillance', 'Alertes', 'Performances'],
		actions: [
			'Consulter les performances d’une application',
			'Voir les alertes en cours',
			'Repérer un ralentissement'
		]
	},
	grafana: {
		tags: ['Tableaux de bord', 'Alertes', 'Mesures'],
		actions: [
			'Consulter un tableau de bord',
			'Récupérer une mesure',
			'Voir les alertes déclenchées'
		]
	},
	pagerduty: {
		tags: ['Alertes', 'Astreintes', 'Incidents'],
		actions: ['Voir les alertes en cours', 'Savoir qui est d’astreinte', 'Suivre un incident']
	},
	incident_io: {
		tags: ['Incidents', 'Suivi', 'Comptes rendus'],
		actions: ['Ouvrir un incident', 'Suivre son avancement', 'Récupérer le compte rendu']
	},
	rootly: {
		tags: ['Incidents', 'Suivi', 'Comptes rendus'],
		actions: ['Déclarer un incident', 'Suivre sa résolution', 'Consulter le compte rendu']
	},
	circleci: {
		tags: ['Builds', 'Tests', 'Suivi'],
		actions: [
			'Consulter l’état d’un build',
			'Relancer une chaîne',
			'Voir pourquoi un test a échoué'
		]
	},
	buildkite: {
		tags: ['Builds', 'Tests', 'Suivi'],
		actions: ['Consulter l’état d’un build', 'Relancer une chaîne', 'Suivre les échecs']
	},
	vercel: {
		tags: ['Déploiements', 'Domaines', 'Journaux'],
		actions: ['Consulter le dernier déploiement', 'Relancer une mise en ligne', 'Lire les journaux']
	},
	render: {
		tags: ['Déploiements', 'Services', 'Journaux'],
		actions: ['Consulter l’état d’un service', 'Relancer un déploiement', 'Lire les journaux']
	},
	railway: {
		tags: ['Déploiements', 'Services', 'Journaux'],
		actions: ['Consulter l’état d’un service', 'Relancer un déploiement', 'Lire les journaux']
	},
	fly: {
		tags: ['Déploiements', 'Machines', 'Journaux'],
		actions: ['Consulter l’état d’une application', 'Relancer un déploiement', 'Lire les journaux']
	},
	digital_ocean: {
		tags: ['Serveurs', 'Bases', 'Suivi'],
		actions: ['Consulter vos serveurs', 'Redémarrer une machine', 'Suivre la consommation']
	},
	cloudflare: {
		tags: ['Domaines', 'Sécurité', 'Cache'],
		actions: ['Consulter vos domaines', 'Vider le cache d’un site', 'Suivre le trafic bloqué']
	},
	supabase: {
		tags: ['Base', 'Tables', 'Utilisateurs'],
		actions: ['Interroger une table', 'Consulter les utilisateurs', 'Suivre l’activité de la base']
	},
	neon: {
		tags: ['Base', 'Branches', 'Requêtes'],
		actions: ['Interroger la base', 'Consulter les branches', 'Suivre la consommation']
	},
	snowflake: {
		tags: ['Requêtes', 'Entrepôt', 'Données'],
		actions: ['Lancer une requête', 'Récupérer un résultat', 'Consulter la consommation']
	},
	databricks: {
		tags: ['Requêtes', 'Traitements', 'Données'],
		actions: ['Lancer une requête', 'Suivre un traitement', 'Récupérer un résultat']
	},
	elasticsearch: {
		tags: ['Rechercher', 'Index', 'Données'],
		actions: ['Chercher dans un index', 'Ajouter un document', 'Consulter l’état du cluster']
	},
	postman: {
		tags: ['API', 'Requêtes', 'Tests'],
		actions: [
			'Lancer une requête depuis une collection',
			'Consulter une collection',
			'Vérifier qu’une API répond'
		]
	},
	figma: {
		tags: ['Maquettes', 'Composants', 'Commentaires'],
		actions: [
			'Retrouver une maquette',
			'Récupérer les composants d’un fichier',
			'Lire les commentaires'
		]
	},
	penpot: {
		tags: ['Maquettes', 'Composants', 'Fichiers'],
		actions: ['Retrouver une maquette', 'Consulter un fichier', 'Récupérer un composant']
	},
	zeplin: {
		tags: ['Maquettes', 'Remise', 'Composants'],
		actions: [
			'Consulter une maquette remise aux développeurs',
			'Récupérer les mesures et les couleurs',
			'Retrouver un composant'
		]
	},
	sourcegraph: {
		tags: ['Rechercher', 'Code', 'Dépôts'],
		actions: [
			'Chercher dans tout votre code',
			'Retrouver où une fonction est utilisée',
			'Comparer entre dépôts'
		]
	},
	npm: {
		tags: ['Paquets', 'Versions', 'Publier'],
		actions: [
			'Consulter un paquet et ses versions',
			'Vérifier ses dépendances',
			'Suivre les téléchargements'
		]
	},
	docker_hub: {
		tags: ['Images', 'Versions', 'Dépôts'],
		actions: [
			'Consulter une image et ses versions',
			'Vérifier une publication',
			'Suivre les téléchargements'
		]
	},

	// ── Modèles IA ───────────────────────────────────────────
	openai: {
		tags: ['Modèles', 'Usage', 'Clés'],
		actions: [
			'Lister les modèles disponibles',
			'Consulter votre consommation',
			'Lancer une génération'
		]
	},
	gemini: {
		tags: ['Modèles', 'Usage', 'Générer'],
		actions: [
			'Lister les modèles disponibles',
			'Lancer une génération',
			'Consulter votre consommation'
		]
	},
	mistral_ai: {
		tags: ['Modèles', 'Usage', 'Générer'],
		actions: [
			'Lister les modèles disponibles',
			'Lancer une génération',
			'Consulter votre consommation'
		]
	},
	deepseek: {
		tags: ['Modèles', 'Usage', 'Générer'],
		actions: [
			'Lister les modèles disponibles',
			'Lancer une génération',
			'Consulter votre consommation'
		]
	},
	hugging_face: {
		tags: ['Modèles', 'Jeux de données', 'Espaces'],
		actions: [
			'Chercher un modèle ou un jeu de données',
			'Consulter une fiche de modèle',
			'Lancer une inférence'
		]
	},
	elevenlabs: {
		tags: ['Voix', 'Générer', 'Bibliothèque'],
		actions: [
			'Transformer un texte en voix',
			'Choisir parmi vos voix',
			'Récupérer le fichier audio'
		]
	},
	replicate: {
		tags: ['Modèles', 'Images', 'Générer'],
		actions: ['Générer une image ou un son', 'Lancer un modèle public', 'Récupérer le résultat']
	},
	openrouter: {
		tags: ['Modèles', 'Usage', 'Coûts'],
		actions: ['Lister les modèles accessibles', 'Lancer une génération', 'Comparer les coûts']
	},
	ollama: {
		tags: ['Modèles', 'Local', 'Générer'],
		actions: [
			'Lister les modèles installés',
			'Lancer une génération en local',
			'Télécharger un nouveau modèle'
		]
	},
	wolfram_alpha_api: {
		tags: ['Calcul', 'Sciences', 'Répondre'],
		actions: [
			'Résoudre un calcul complexe',
			'Obtenir une donnée scientifique',
			'Convertir des unités'
		]
	}
};

/** Fiche du catalogue recommande, ou null hors de ce perimetre. */
export const ficheCatalogueDe = (slug: string): FicheCatalogue | null =>
	FICHES_CATALOGUE[`${slug}`.toLowerCase()] ?? null;
