// Source unique des 9 dossiers PARA du coffre (squelette figé, jamais renommé par le dirigeant).
// Miroir front de VAULT_STRUCTURE (app/bridge/src/providers_bridge/memory_adapter.py) : si un
// dossier est ajouté/renommé côté bridge, ce tableau est le SEUL endroit à corriger côté front —
// MemoryExplorer.svelte (UI) et templates.ts (prompt de l'Agent Obsidian) en dérivent tous les deux.

export type VaultFolderInfo = {
	slug: string; // nom réel du dossier sur disque (chemin racine du coffre)
	label: string; // libellé court affiché à l'écran (langage dirigeant)
	subtitle: string; // sous-titre affiché sous le dossier dans l'arbre « Mes notes »
	agentNote: string; // description utilisée dans le prompt de l'Agent Obsidian (templates.ts)
};

export const VAULT_FOLDERS: VaultFolderInfo[] = [
	{
		slug: '00-Réception',
		label: 'Réception',
		subtitle: "Tout arrive ici avant d'être rangé",
		agentNote: "tout ce que tu captures arrive ICI d'abord (jamais ailleurs)."
	},
	{
		slug: '01-En cours',
		label: 'En cours',
		subtitle: 'Ce sur quoi vous travaillez en ce moment',
		agentNote: 'travaux en cours avec un objectif ou une échéance.'
	},
	{
		slug: '02-Mes responsabilités',
		label: 'Mes responsabilités',
		subtitle: 'Ce dont vous vous occupez en continu (ventes, équipe, finances…)',
		agentNote: 'responsabilités durables (clients, finance, équipe, produit…).'
	},
	{
		slug: '03-Idées & ressources',
		label: 'Idées & ressources',
		subtitle: 'Documents et idées utiles à garder sous la main',
		agentNote: 'références, procédures, documentation.'
	},
	{
		slug: '04-Archivées',
		label: 'Archivées',
		subtitle: 'Ce qui est terminé, conservé au cas où',
		agentNote: 'terminé ou inactif (on archive, on ne supprime jamais).'
	},
	{
		slug: '05-Journal',
		label: 'Journal',
		subtitle: 'Vos notes datées : réunions, décisions, journées',
		agentNote: 'notes datées (journées, réunions) au format AAAA-MM-JJ.'
	},
	{
		slug: '06-Contacts',
		label: 'Contacts',
		subtitle: 'Vos clients, prospects et partenaires',
		agentNote: 'une fiche par client ou contact, reliée à ses projets et échanges.'
	},
	{
		slug: '07-Mes réflexions',
		label: 'Mes réflexions',
		subtitle: 'Là où vous posez vos idées et vos notes',
		agentNote: 'les prises de position et idées personnelles du dirigeant, plus une carte par domaine.'
	},
	{
		slug: '08-Modèles de notes',
		label: 'Modèles de notes',
		subtitle: 'Des exemples prêts à réutiliser (compte-rendu, fiche client…)',
		agentNote: "un modèle par type de note ; utilise-le, n'improvise pas la structure."
	}
];

// Dérivés pratiques (évitent de reconstruire un Record à chaque usage).
export const FRIENDLY_FOLDER: Record<string, string> = Object.fromEntries(
	VAULT_FOLDERS.map((f) => [f.slug, f.label])
);

export const FOLDER_SUBTITLE: Record<string, string> = Object.fromEntries(
	VAULT_FOLDERS.map((f) => [f.slug, f.subtitle])
);
