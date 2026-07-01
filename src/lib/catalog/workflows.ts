/**
 * Catalogue curé des workflows métier (feature 008, Vague 3).
 *
 * Chaque workflow est une amorce de conversation : un libellé + une description orientés dirigeant,
 * et un prompt français solide pré-rempli dans le chat (l'utilisateur valide avant d'envoyer — D27).
 * Aucune garantie d'exécution n'est promise : c'est l'assistant qui agit avec ses outils.
 *
 * Extensible : ajouter une entrée suffit.
 */

export type Workflow = {
	id: string;
	label: string;
	description: string;
	/** Pictogramme simple (emoji) pour repère visuel rapide. */
	icon: string;
	/** Prompt pré-rempli dans le chat. */
	prompt: string;
};

export const WORKFLOWS: Workflow[] = [
	{
		id: 'brief-matin',
		label: 'Brief du matin',
		description: 'Un résumé de ce qui compte aujourd’hui et des décisions en attente.',
		icon: '☀️',
		prompt:
			'Fais-moi le brief du matin pour mon entreprise : ce qui demande mon attention aujourd’hui, ' +
			'les décisions en attente, les engagements à tenir et les priorités. Va à l’essentiel, en français.'
	},
	{
		id: 'resumer-emails',
		label: 'Résumer mes emails',
		description: 'Synthèse des emails importants et liste des actions à faire.',
		icon: '✉️',
		prompt:
			'Résume mes emails récents non traités : regroupe par sujet, identifie ce qui est urgent, ' +
			'et propose une liste d’actions concrètes avec une suggestion de réponse quand c’est pertinent.'
	},
	{
		id: 'veille-concurrentielle',
		label: 'Veille concurrentielle',
		description: 'Ce que font mes concurrents et les opportunités à saisir.',
		icon: '🔭',
		prompt:
			'Fais une veille concurrentielle sur mon secteur : tendances récentes, mouvements des concurrents, ' +
			'opportunités et menaces. Termine par 3 recommandations actionnables pour mon entreprise.'
	},
	{
		id: 'preparer-reunion',
		label: 'Préparer une réunion',
		description: 'Ordre du jour, points clés et questions à poser.',
		icon: '🗓️',
		prompt:
			'Aide-moi à préparer une réunion. Pose-moi d’abord les questions nécessaires (objectif, participants, ' +
			'contexte), puis propose un ordre du jour, les points clés à aborder et les questions à poser.'
	},
	{
		id: 'plan-action-semaine',
		label: 'Plan d’action de la semaine',
		description: 'Les priorités de la semaine, organisées et réalistes.',
		icon: '✅',
		prompt:
			'Aide-moi à bâtir mon plan d’action de la semaine : à partir de mes objectifs et de ce qui est en cours, ' +
			'propose des priorités réalistes, organisées par jour, avec les actions concrètes à faire.'
	},
	{
		id: 'post-linkedin',
		label: 'Rédiger un post LinkedIn',
		description: 'Un post professionnel prêt à publier, à ta voix.',
		icon: '📝',
		prompt:
			'Rédige un post LinkedIn professionnel pour mon entreprise. Demande-moi d’abord le sujet et l’angle, ' +
			'puis propose un post clair, engageant et authentique, avec quelques variantes d’accroche.'
	},
	{
		id: 'analyser-document',
		label: 'Analyser un document',
		description: 'Résumé, points clés et risques d’un document.',
		icon: '📄',
		prompt:
			'Je vais te partager un document. Résume-le, dégage les points clés, signale les risques ou points ' +
			'd’attention, et propose les prochaines actions. Dis-moi quel document analyser.'
	},
	{
		id: 'rediger-email',
		label: 'Rédiger un email',
		description: 'Un email clair et professionnel en quelques secondes.',
		icon: '📧',
		prompt:
			'Aide-moi à rédiger un email professionnel. Demande-moi le destinataire, l’objectif et le ton souhaité, ' +
			'puis propose un email clair et bien tourné en français.'
	},
	{
		id: 'second-cerveau',
		label: 'Fouiller mon second cerveau',
		description: 'Retrouve une info dans vos notes et fait le point.',
		icon: '🧠',
		prompt:
			'Cherche dans mon second cerveau (mes notes) ce que je sais sur un sujet et fais-moi une synthèse ' +
			'claire, avec les points clés et ce qui manque éventuellement. Demande-moi le sujet si besoin.'
	},
	{
		id: 'deleguer-agent',
		label: 'Déléguer à un agent',
		description: 'Confiez une mission à un collègue numérique spécialisé.',
		icon: '🤖',
		prompt:
			'Je veux déléguer une tâche à un agent spécialisé. Demande-moi laquelle et le résultat attendu, ' +
			'puis propose comment un agent dédié s’en chargerait (mission, méthode, garde-fous) et lance-toi.'
	}
];
