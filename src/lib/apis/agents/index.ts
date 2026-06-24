import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de la page Agents (Agent OS). Appelle le router admin /api/v1/agents,
// qui proxifie vers le Providers Bridge. Un agent = un profil Hermes (source de vérité unique).

// Helper interne : un appel JSON authentifié vers /api/v1/agents, gestion d'erreur uniforme.
const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents${path}`, {
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

	if (error) {
		throw error;
	}

	return res;
};

// Liste les agents (profils Hermes)
export const getAgents = (token: string) => call(token, 'GET', '/');

// Crée un agent (clone la config du profil actif). { name, description?, soul? }
export const createAgent = (
	token: string,
	payload: { name: string; description?: string; soul?: string }
) => call(token, 'POST', '/', payload);

// Bascule l'agent « de garde »
export const setActiveAgent = (token: string, name: string) => call(token, 'POST', '/active', { name });

// Supprime un agent (l'agent par défaut est protégé côté bridge)
export const deleteAgent = (token: string, name: string) =>
	call(token, 'DELETE', `/${encodeURIComponent(name)}`);

// Mission (SOUL.md)
export const getAgentSoul = (token: string, name: string) =>
	call(token, 'GET', `/${encodeURIComponent(name)}/soul`);

export const updateAgentSoul = (token: string, name: string, content: string) =>
	call(token, 'PUT', `/${encodeURIComponent(name)}/soul`, { content });

// Description (résumé du rôle)
export const updateAgentDescription = (token: string, name: string, description: string) =>
	call(token, 'PUT', `/${encodeURIComponent(name)}/description`, { description });
