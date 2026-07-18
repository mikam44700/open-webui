// L'équipe LunarIA dans le chat (SPEC-chat-agentique).
//
// Un agent de l'équipe = une entrée `model` open-webui seedée par backend/seed_agents.py,
// reconnaissable à son tag « Équipe LunarIA ». Pas d'état global d'agent actif : l'agent
// avec qui on parle EST le modèle sélectionné du chat (un seul système, leçon de l'audit v1).

export const TEAM_TAG = 'Équipe LunarIA';

export type TeamAgentView = {
	id: string;
	firstName: string;
	tagline: string;
	description: string;
	avatarUrl: string;
	suggestions: { content: string }[];
};

const metaOf = (model: any) => model?.info?.meta ?? model?.meta ?? {};

export const isTeamAgent = (model: any): boolean =>
	(metaOf(model)?.tags ?? []).some((tag: any) => tag?.name === TEAM_TAG);

export const teamAgents = (models: any[]): TeamAgentView[] =>
	(models ?? []).filter(isTeamAgent).map(agentView).filter(Boolean) as TeamAgentView[];

export const agentView = (model: any): TeamAgentView | null => {
	if (!model) return null;
	const meta = metaOf(model);
	return {
		id: model.id,
		firstName: model.name ?? model.id,
		tagline: meta.tagline ?? '',
		description: meta.description ?? '',
		avatarUrl: meta.profile_image_url ?? '/favicon.png',
		suggestions: meta.suggestion_prompts ?? []
	};
};

// Repli d'avatar pour un <img> : favicon si l'image de l'agent manque.
export const avatarImgFallback = (e: Event): void => {
	const el = e.currentTarget as HTMLImageElement | null;
	if (el) el.src = '/favicon.png';
};
