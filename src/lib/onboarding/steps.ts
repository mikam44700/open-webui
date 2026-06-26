/**
 * Dérivation de la checklist d'onboarding (feature 009, Vague 3).
 *
 * Fonction PURE : à partir des états déjà chargés par le tableau de bord, calcule les étapes de mise
 * en route et leur complétion. Honnêteté (D27) : une étape n'est `done` que si l'état est réellement
 * vérifié ; un état `unknown` (source non joignable) ne coche jamais une étape.
 */

export type OnboardingInput = {
	/** Un modèle IA est-il actif ? */
	activeBrain: boolean | 'unknown';
	/** Nombre d'intégrations connectées. */
	connectedIntegrations: number | 'unknown';
	/** Mémoire accessible. */
	memory: 'ok' | 'down' | 'unknown';
	/** Messagerie démarrée. */
	messaging: 'ok' | 'down' | 'unknown';
	/** Nombre total de tâches. */
	taskCount: number | 'unknown';
};

export type OnboardingStep = {
	id: string;
	label: string;
	hint: string;
	done: boolean;
	href: string;
};

export const deriveOnboardingSteps = (i: OnboardingInput): OnboardingStep[] => [
	{
		id: 'brain',
		label: 'Choisir un modèle IA',
		hint: 'Sélectionnez le cerveau de votre assistant.',
		done: i.activeBrain === true,
		href: '/providers'
	},
	{
		id: 'tools',
		label: 'Connecter un outil',
		hint: 'Branchez vos applications (Google, Email, Notion…).',
		done: typeof i.connectedIntegrations === 'number' && i.connectedIntegrations > 0,
		href: '/connectors'
	},
	{
		id: 'memory',
		label: 'Activer la mémoire',
		hint: 'Donnez à votre assistant la mémoire de votre activité.',
		done: i.memory === 'ok',
		href: '/memory'
	},
	{
		id: 'messaging',
		label: 'Configurer la messagerie',
		hint: 'Parlez à votre assistant sur vos canaux habituels.',
		done: i.messaging === 'ok',
		href: '/gateway'
	},
	{
		id: 'task',
		label: 'Créer une première tâche',
		hint: 'Déléguez une première mission à votre assistant.',
		done: typeof i.taskCount === 'number' && i.taskCount > 0,
		href: '/kanban'
	}
];

/** Nombre d'étapes réalisées. */
export const onboardingProgress = (steps: OnboardingStep[]): number =>
	steps.filter((s) => s.done).length;

/** Toutes les étapes sont-elles réalisées ? */
export const onboardingComplete = (steps: OnboardingStep[]): boolean => steps.every((s) => s.done);
