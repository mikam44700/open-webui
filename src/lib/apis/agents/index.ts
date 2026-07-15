import { apiCall } from '$lib/apis/apiCall';

// Client API de la page Agents (Agent OS). Appelle le router admin /api/v1/agents,
// qui proxifie vers le Providers Bridge. Un agent = un profil Hermes (source de vérité unique).

// Helper interne : un appel JSON authentifié vers /api/v1/agents, gestion d'erreur uniforme
// (mutualisée dans $lib/apis/apiCall — voir ce module pour le détail du comportement).
const call = (token: string, method: string, path: string, body?: unknown) =>
	apiCall(token, '/agents', method, path, body);

// Liste les agents (profils Hermes)
export const getAgents = (token: string) => call(token, 'GET', '/');

// Crée un agent (clone la config du profil actif). { name, description?, soul?, avatar? }
export const createAgent = (
	token: string,
	payload: { name: string; description?: string; soul?: string; avatar?: string }
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

// Avatar (visage de l'agent) — chemin d'image, ou null pour le retirer.
export const updateAgentAvatar = (token: string, name: string, avatar: string | null) =>
	call(token, 'PUT', `/${encodeURIComponent(name)}/avatar`, { avatar });

// Outils PAR AGENT : compétences + connecteurs MCP avec leur état pour cet agent.
export const getAgentTools = (token: string, name: string) =>
	call(token, 'GET', `/${encodeURIComponent(name)}/tools`);

// Active/désactive une compétence pour cet agent.
export const setAgentSkill = (token: string, name: string, skill: string, enabled: boolean) =>
	call(token, 'POST', `/${encodeURIComponent(name)}/tools/skill`, { name: skill, enabled });

// Active/désactive un connecteur MCP pour cet agent.
export const setAgentMcp = (token: string, name: string, mcp: string, enabled: boolean) =>
	call(token, 'POST', `/${encodeURIComponent(name)}/tools/mcp`, { name: mcp, enabled });
