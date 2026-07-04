/**
 * Cartes d'action par agent + résolution de l'agent actif pour l'accueil du chat.
 *
 * Objectif (inspiré de Limova) : quand un agent est actif (ex. Emma), le chat vide affiche
 * son avatar + son prénom + son rôle, et propose SES actions concrètes en cartes cliquables.
 * Honnêteté (D27) : cliquer une carte PRÉ-REMPLIT le chat — l'utilisateur relit et envoie ;
 * aucune exécution automatique n'est promise (c'est l'agent qui agit avec ses outils).
 *
 * Extensible : ajouter une entrée dans AGENT_ACTIONS (clé = identifiant d'avatar) suffit.
 */

import { AGENT_TEMPLATES } from '$lib/components/agents/templates';
import { avatarId, avatarImage } from '$lib/components/agents/avatars';
import { prettifyName, slugify } from '$lib/components/agents/utils';

// Même forme qu'un Workflow (catalog/workflows.ts) → réutilisable dans la même grille de cartes.
export type ActionCard = {
	id: string;
	label: string;
	description: string;
	/** Pictogramme simple (emoji). */
	icon: string;
	/** Image optionnelle (URL/chemin) — si fournie, remplace l'emoji dans la carte. */
	image?: string;
	/** Prompt pré-rempli dans le chat au clic. */
	prompt: string;
};

// Agent tel que renvoyé par getAgents() (sous-ensemble utile ici).
type AgentDTO = {
	name: string;
	description?: string;
	avatar?: string | null;
	active?: boolean;
	is_default?: boolean;
};

// Vue d'affichage d'un agent dans l'accueil du chat.
export type AgentView = {
	name: string; // identifiant du profil Hermes
	firstName: string; // prénom vedette (ex. « Emma ») ou nom lisible en repli
	role: string; // fonction (sous-titre), vide si inconnu
	description: string;
	avatar: string; // URL d'image (avec repli /favicon.png géré à l'affichage)
	actions: ActionCard[]; // cartes curées (peut être vide → on retombe sur le catalogue générique)
};

/**
 * Cartes d'action curées PAR AGENT. Clé = identifiant d'avatar (emma, mike, …),
 * car c'est le lien le plus fiable entre un agent (profil Hermes) et son personnage.
 */
export const AGENT_ACTIONS: Record<string, ActionCard[]> = {
	emma: [
		{
			id: 'emma-tri-mails',
			label: 'Trier mes emails',
			description: 'Urgent / à répondre / pour info + brouillons prêts à valider.',
			icon: '✉️',
			prompt:
				'Passe en revue mes emails récents non traités et trie-les en « urgent / à répondre / pour info ». ' +
				'Pour chaque email important, résume-le en une ligne et prépare un brouillon de réponse que je pourrai valider.'
		},
		{
			id: 'emma-agenda-semaine',
			label: 'Organiser ma semaine',
			description: 'Point sur l’agenda, conflits repérés, créneaux de concentration protégés.',
			icon: '🗓️',
			prompt:
				'Fais le point sur mon agenda de la semaine : liste mes rendez-vous, repère les conflits ou les journées ' +
				'trop chargées, et propose une organisation qui protège mes créneaux de concentration.'
		},
		{
			id: 'emma-rappels',
			label: 'Préparer mes rappels',
			description: 'Les rendez-vous et échéances à venir, avec les rappels à programmer.',
			icon: '⏰',
			prompt:
				'Prépare la liste de mes rendez-vous et échéances importantes à venir, et propose-moi les rappels ' +
				'à programmer pour ne rien laisser passer.'
		}
	]
};

/**
 * Construit la vue d'accueil d'un agent actif.
 * Retourne null si aucun agent exploitable (ex. profil « default » non personnalisé) →
 * l'accueil générique existant est conservé (zéro régression).
 */
export const resolveAgentView = (agent: AgentDTO | null | undefined): AgentView | null => {
	if (!agent) return null;

	const aid = avatarId(agent.avatar);
	const tpl = AGENT_TEMPLATES.find(
		(t) =>
			(t.image && avatarId(t.image) === aid) || t.id === agent.name || slugify(t.label) === agent.name
	);

	// Profil de base non identifié → on garde l'accueil générique (« Bonjour {prénom} »).
	if (!tpl && agent.is_default) return null;

	const firstName = tpl?.firstName ?? prettifyName(agent.name);
	const role = tpl?.role ?? '';
	const description = agent.description ?? tpl?.description ?? '';
	// Priorité : avatar persisté → image du template → avatar déduit de l'id → favicon.
	const avatar = agent.avatar || tpl?.image || (aid ? avatarImage(aid) : '/favicon.png');
	const actions = (aid && AGENT_ACTIONS[aid]) || [];

	return { name: agent.name, firstName, role, description, avatar, actions };
};
