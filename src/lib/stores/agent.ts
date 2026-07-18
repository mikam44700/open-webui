// Store de l'agent actif (profil Hermes servant le chat).
//
// Source de vérité = le bridge (/api/agents, champ `active`). On le charge une fois et
// on l'expose globalement pour que l'en-tête du chat et les bulles de réponse puissent
// incarner l'interlocuteur (avatar + prénom, ex. « Mike »). Best-effort : en cas d'échec,
// le store reste nul et le chat retombe sur son affichage natif (nom du modèle + favicon).

import { writable } from 'svelte/store';
import { getAgents } from '$lib/apis/agents';

export type ActiveAgent = { name: string; description?: string | null; avatar?: string | null } | null;

export const activeAgent = writable<ActiveAgent>(null);

let loaded = false;

// Charge l'agent actif si ce n'est pas déjà fait. `force` recharge (après un changement d'agent).
export const ensureActiveAgent = async (token: string, force = false): Promise<void> => {
	if (!token || (loaded && !force)) return;
	loaded = true;
	try {
		const res = await getAgents(token);
		const list = Array.isArray(res?.agents) ? res.agents : [];
		activeAgent.set(list.find((a: { active?: boolean }) => a?.active) ?? null);
	} catch (e) {
		// On n'incarne pas plutôt que d'afficher un état faux : on réautorise un retry.
		loaded = false;
		console.error('activeAgent: chargement impossible', e);
	}
};
