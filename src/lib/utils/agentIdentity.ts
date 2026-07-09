// Identité d'affichage d'un agent (profil Hermes) dans le chat : prénom + avatar.
//
// Côté bridge, l'agent actif porte un identifiant technique (ex. « default ») et un
// chemin d'avatar (ex. « /assets/agents/mike.png »). Pour l'incarner dans le chat, on
// dérive un prénom lisible : d'abord depuis l'avatar (mike.png -> « Mike », via le
// manifeste avatars.ts), à défaut depuis le nom de profil embelli.

import { avatarFromImage } from '$lib/components/agents/avatars';

export type AgentLike = { name?: string; description?: string | null; avatar?: string | null };

export type AgentIdentity = {
	firstName: string;
	avatarUrl: string | null;
	initial: string;
};

// Embellit un identifiant de profil en libellé (« assistant-rh » -> « Assistant Rh »).
const beautify = (slug: string): string =>
	(slug || '')
		.replace(/[-_]+/g, ' ')
		.replace(/\b\w/g, (c) => c.toUpperCase())
		.trim();

export const agentIdentity = (agent?: AgentLike | null): AgentIdentity | null => {
	if (!agent) return null;
	const fromAvatar = avatarFromImage(agent.avatar ?? undefined);
	const firstName = fromAvatar?.label || beautify(agent.name ?? '') || 'Assistant';
	return {
		firstName,
		avatarUrl: agent.avatar ?? null,
		initial: firstName.charAt(0).toUpperCase()
	};
};
