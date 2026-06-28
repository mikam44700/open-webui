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
	}
};
