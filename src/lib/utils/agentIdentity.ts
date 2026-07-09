// Identité d'affichage d'un agent (profil Hermes) dans le chat : prénom + avatar.
//
// Côté bridge, l'agent actif porte un identifiant technique (ex. « default ») et un
// chemin d'avatar (ex. « /assets/agents/mike.png »). Pour l'incarner dans le chat, on
// dérive un prénom lisible : d'abord depuis l'avatar (mike.png -> « Mike », via le
// manifeste avatars.ts), à défaut depuis le nom de profil embelli.

import { avatarFromImage, faceFromImage } from '$lib/components/agents/avatars';

export type AgentLike = { name?: string; description?: string | null; avatar?: string | null };

export type AgentIdentity = {
	firstName: string;
	avatarUrl: string | null;
	faceUrl: string | null; // gros plan visage pour l'affichage en cercle (repli sur avatarUrl)
	initial: string;
};

// Repli d'avatar en cascade pour un <img> circulaire : visage -> corps entier -> favicon.
// À brancher sur on:error ; `body` est l'image d'origine (corps entier) si connue.
export const avatarImgFallback = (e: Event, body?: string | null): void => {
	const el = e.currentTarget as HTMLImageElement | null;
	if (!el) return;
	if (body && !el.dataset.triedBody) {
		el.dataset.triedBody = '1';
		el.src = body;
		return;
	}
	el.src = '/favicon.png';
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
		faceUrl: faceFromImage(agent.avatar ?? undefined),
		initial: firstName.charAt(0).toUpperCase()
	};
};
