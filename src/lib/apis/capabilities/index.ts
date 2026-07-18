import { apiCall } from '$lib/apis/apiCall';

// Client API de la page Capacités (Agent OS). Appelle le router admin /api/v1/capabilities,
// qui proxifie vers le Providers Bridge (capacités natives de Hermes — source de vérité unique).
// Outils = toolsets natifs Hermes ; Compétences = skills Hermes. Les connecteurs MCP, troisième
// volet de la page, ont leur propre client (apis/connectors).

// Helper interne : un appel JSON authentifié vers /api/v1/capabilities, gestion d'erreur uniforme
// (mutualisée dans $lib/apis/apiCall).
const call = (token: string, method: string, path: string, body?: unknown) =>
	apiCall(token, '/capabilities', method, path, body);

// Outils (toolsets natifs Hermes)
export const getTools = (token: string) => call(token, 'GET', '/tools');

// L'appel bridge /tools coûte ~2,5 s (sous-process Hermes, 25 toolsets) et n'a pas de cache
// serveur → l'onglet Outils affichait un spinner à chaque ouverture. On ajoute un cache mémoire
// de session (TTL court) + un prefetch déclenché à l'ouverture de la page Capacités, pour que la
// liste soit déjà prête au clic. Invalidé à chaque bascule d'outil (état toujours frais).
let _toolsCache: { at: number; promise: Promise<unknown> } | null = null;
const TOOLS_TTL_MS = 60_000;

export const getToolsCached = (token: string): Promise<unknown> => {
	if (_toolsCache && Date.now() - _toolsCache.at < TOOLS_TTL_MS) return _toolsCache.promise;
	const promise = getTools(token).catch((err) => {
		_toolsCache = null; // un échec ne doit pas rester en cache
		throw err;
	});
	_toolsCache = { at: Date.now(), promise };
	return promise;
};

// Prefetch best-effort (ne jette jamais) : à appeler dès l'ouverture de la page Capacités.
export const prefetchTools = (token: string): void => {
	void getToolsCached(token).catch(() => {});
};

// À appeler après une bascule d'outil pour éviter de resservir un état périmé.
export const invalidateToolsCache = (): void => {
	_toolsCache = null;
};

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

// Crawl4AI : lecture web approfondie installée à la demande (conteneur Docker + connecteur MCP).
export const getCrawl4aiStatus = (token: string) => call(token, 'GET', '/crawl4ai/status');

export const installCrawl4ai = (token: string) => call(token, 'POST', '/crawl4ai/install');

export const uninstallCrawl4ai = (token: string) => call(token, 'POST', '/crawl4ai/uninstall');

// Mise à jour Crawl4AI (versions épinglées, même principe que le moteur Hermes).
export const checkCrawl4aiUpdate = (token: string) => call(token, 'POST', '/crawl4ai/update/check');

export const startCrawl4aiUpdate = (token: string) => call(token, 'POST', '/crawl4ai/update/start');

export const getCrawl4aiUpdateStatus = (token: string) =>
	call(token, 'GET', '/crawl4ai/update/status');
