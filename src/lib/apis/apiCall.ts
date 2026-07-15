import { WEBUI_API_BASE_URL } from '$lib/constants';

// Helper HTTP partagé par les modules apis/ maison (agents, memory, kanban, calendrier Hermes,
// automations Hermes, capacités, connecteurs, gateway, Google, intégrations…).
// Centralise un pattern recopié à l'identique dans ~10 fichiers : même fetch + Authorization,
// même parsing JSON, même détail d'erreur remonté (`err.detail ?? err`), même log console.
// Comportement STRICTEMENT inchangé — chaque module ne fait plus que fournir son segment de base
// (ex : '/memory', '/agents') à son propre wrapper `call(token, method, path, body)`.
export const apiCall = async (
	token: string,
	baseSegment: string,
	method: string,
	path: string,
	body?: unknown
): Promise<any> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}${baseSegment}${path}`, {
		method,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});

	if (error) throw error;
	return res;
};
