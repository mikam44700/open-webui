// Correspondance agent adopté ↔ template métier. Un agent créé porte le slug du libellé de son
// template (même règle que le bridge) ; on retrouve donc son template par id/label/avatar pour
// réutiliser son image, sa couleur et savoir s'il est déjà adopté. Partagé (AgentList + Catalogue).
import { AGENT_TEMPLATES, type AgentTemplate } from './templates';
import { slugify } from './utils';
import { avatarId } from './avatars';

export type AgentLike = { name: string; avatar?: string | null };

export const matchTemplate = (a: AgentLike): AgentTemplate | null =>
	AGENT_TEMPLATES.find(
		(x) =>
			x.id === a.name ||
			slugify(x.label) === a.name ||
			(!!x.image && !!a.avatar && avatarId(x.image) === avatarId(a.avatar))
	) ?? null;

// Ensemble des ids de templates déjà adoptés (résolus de façon fiable même si le nom diffère de l'id).
export const adoptedTemplateIds = (agents: AgentLike[]): Set<string> =>
	new Set(agents.map((a) => matchTemplate(a)?.id).filter(Boolean) as string[]);
