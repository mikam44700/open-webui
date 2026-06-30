import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API de la page Capacités (Agent OS). Appelle le router admin /api/v1/capabilities,
// qui proxifie vers le Providers Bridge (capacités natives de Hermes — source de vérité unique).
// Outils = toolsets natifs Hermes ; Compétences = skills Hermes. Les connecteurs MCP, troisième
// volet de la page, ont leur propre client (apis/connectors).

// Helper interne : un appel JSON authentifié vers /api/v1/capabilities, gestion d'erreur uniforme.
const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/capabilities${path}`, {
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

// Outils (toolsets natifs Hermes)
export const getTools = (token: string) => call(token, 'GET', '/tools');

export const setToolEnabled = (token: string, name: string, enabled: boolean) =>
	call(token, 'PATCH', `/tools/${encodeURIComponent(name)}`, { enabled });

// Compétences (skills natives Hermes)
export const getSkills = (token: string) => call(token, 'GET', '/skills');

export const setSkillEnabled = (token: string, name: string, enabled: boolean) =>
	call(token, 'PATCH', `/skills/${encodeURIComponent(name)}`, { enabled });

// Compétences « maison » (sur mesure, créées par le client) — page Compétences de l'Espace de travail.
export const getCustomSkills = (token: string) => call(token, 'GET', '/custom-skills');

// Contenu complet d'une compétence maison (procédure incluse), pour l'affichage en détail.
export const getCustomSkill = (token: string, name: string) =>
	call(token, 'GET', `/custom-skills/${encodeURIComponent(name)}`);

export const createCustomSkill = (
	token: string,
	label: string,
	description: string,
	instructions: string,
	category: string = 'Autres'
) => call(token, 'POST', '/custom-skills', { label, description, instructions, category });

export const deleteCustomSkill = (token: string, name: string) =>
	call(token, 'DELETE', `/custom-skills/${encodeURIComponent(name)}`);

// Connexion des outils (feature 003) — métadonnées, clé/champs, OAuth, test, déconnexion.
export const getToolConnection = (token: string, name: string) =>
	call(token, 'GET', `/tools/${encodeURIComponent(name)}/connection`);

export const setToolKey = (token: string, name: string, values: Record<string, string>) =>
	call(token, 'PUT', `/tools/${encodeURIComponent(name)}/key`, { values });

export const testToolConnection = (token: string, name: string) =>
	call(token, 'POST', `/tools/${encodeURIComponent(name)}/test`);

// Test RÉEL d'une clé/URL d'un fournisseur (appel HTTP côté bridge).
export const testToolKey = (token: string, name: string, values: Record<string, string>) =>
	call(token, 'POST', `/tools/${encodeURIComponent(name)}/test-key`, { values });

export const disconnectTool = (token: string, name: string) =>
	call(token, 'DELETE', `/tools/${encodeURIComponent(name)}/connection`);

// Déconnecte UN seul fournisseur (efface ses champs, sans désactiver l'outil entier).
export const disconnectToolProvider = (token: string, name: string, keys: string[]) =>
	call(token, 'POST', `/tools/${encodeURIComponent(name)}/disconnect-provider`, { keys });

export const startToolOAuth = (token: string, name: string) =>
	call(token, 'POST', `/tools/${encodeURIComponent(name)}/oauth/start`);

export const getToolOAuthStatus = (token: string, name: string) =>
	call(token, 'GET', `/tools/${encodeURIComponent(name)}/oauth/status`);

// SearXNG : recherche web souveraine installée à la demande (conteneur Docker).
export const getSearxngStatus = (token: string) => call(token, 'GET', '/searxng/status');

export const installSearxng = (token: string) => call(token, 'POST', '/searxng/install');

export const uninstallSearxng = (token: string) => call(token, 'POST', '/searxng/uninstall');
