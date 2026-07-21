// Adaptateur « agents » (SPEC-chat-agentique, portage fidèle du chat v1).
//
// La v1 interrogeait les profils du moteur Hermes (/api/v1/agents, bridge). Chez nous,
// UN SEUL système (leçon de l'audit) : un agent de l'équipe = une entrée `model`
// open-webui taguée « Équipe LunarIA » (seed_agents.py). Ce module sert la MÊME forme
// de données que l'API v1 aux composants portés (AgentSelector, Placeholder, stores) —
// aucun changement visuel, seule la source change.
//
// « Agent actif » : choix client persisté (localStorage) ; la Navbar synchronise le
// modèle sélectionné du chat dessus (l'agent EST le modèle, Hermes applique sa mission).

import { WEBUI_API_BASE_URL } from '$lib/constants';

const TEAM_TAG = 'Équipe LunarIA';
const ACTIVE_KEY = 'lunaria-active-agent';
const SEEDED_TEAM_AGENT_IDS = new Set(['luna', 'mike', 'victor', 'lea', 'sacha', 'theo', 'clara']);

// L'API /models retire volontairement profile_image_url de ses réponses. Les sept agents
// LunarIA ont cependant des portraits statiques livrés avec l'app ; on restaure ici leur
// chemin source afin que tous les consommateurs (sélecteur, badge, messages) puissent en
// déduire le gros plan /static/agents/faces/<id>.png. Un futur agent personnalisé passe par
// l'endpoint officiel de profil du modèle.
const modelAvatarUrl = (id: string, metaAvatar?: string | null): string =>
	metaAvatar ||
	(SEEDED_TEAM_AGENT_IDS.has(id)
		? `/static/agents/${id}.png`
		: `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(id)}`);

export type AgentDTO = {
	name: string;
	description?: string | null;
	avatar?: string | null;
	active?: boolean;
	is_default?: boolean;
	role?: string;
	suggestions?: { content: string }[];
};

export const getActiveAgentId = (): string => {
	try {
		return localStorage.getItem(ACTIVE_KEY) || 'luna';
	} catch {
		return 'luna';
	}
};

export const getAgents = async (token: string): Promise<{ agents: AgentDTO[] }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/models`, {
		method: 'GET',
		headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
	}).then(async (r) => {
		if (!r.ok) throw await r.json();
		return r.json();
	});

	const models = res?.data ?? res ?? [];
	const activeId = getActiveAgentId();
	const agents: AgentDTO[] = models
		.filter((m: any) =>
			((m?.info?.meta ?? m?.meta)?.tags ?? []).some((t: any) => t?.name === TEAM_TAG)
		)
		.map((m: any) => {
			const meta = m?.info?.meta ?? m?.meta ?? {};
			return {
				name: m.id,
				description: meta.description ?? '',
				avatar: modelAvatarUrl(m.id, meta.profile_image_url),
				active: m.id === activeId,
				is_default: false,
				role: meta.tagline ?? '',
				suggestions: meta.suggestion_prompts ?? []
			};
		});

	// Si l'agent actif persisté n'existe plus, le premier de l'équipe reprend le flambeau.
	if (agents.length > 0 && !agents.some((a) => a.active)) {
		agents[0].active = true;
	}
	return { agents };
};

export const setActiveAgent = async (_token: string, name: string): Promise<void> => {
	try {
		localStorage.setItem(ACTIVE_KEY, name);
	} catch {
		// stockage indisponible (navigation privée) : le choix vaut pour la session en cours
	}
};
