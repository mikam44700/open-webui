import {
	ajouterServeurMcp,
	basculerCompetence,
	basculerOutil,
	enregistrerClesOutil,
	getCatalogueMcp,
	getCompetences,
	getConfigurationOutil,
	getInventaireOutils,
	getServeursMcp,
	installerMcp,
	retirerCleFournisseur
} from '$lib/apis/hermes';

export const getTools = async (token: string) => {
	const result = await getInventaireOutils(token);
	const list = Array.isArray(result) ? result : (result?.toolsets ?? []);
	return {
		toolsets: list.map((tool: any) => ({
			...tool,
			connection_state: tool.configured ? 'connected' : 'connection_required',
			providers: tool.providers ?? []
		}))
	};
};

let toolsCache: { at: number; promise: Promise<unknown> } | null = null;
const TOOLS_TTL_MS = 60_000;

export const getToolsCached = (token: string) => {
	if (toolsCache && Date.now() - toolsCache.at < TOOLS_TTL_MS) return toolsCache.promise;
	const promise = getTools(token).catch((error) => {
		toolsCache = null;
		throw error;
	});
	toolsCache = { at: Date.now(), promise };
	return promise;
};

export const prefetchTools = (token: string) => void getToolsCached(token).catch(() => {});
export const invalidateToolsCache = () => {
	toolsCache = null;
};

export const setToolEnabled = async (token: string, name: string, enabled: boolean) => {
	const result = await basculerOutil(token, name, enabled);
	invalidateToolsCache();
	return result;
};

export const getSkills = async (token: string) => {
	const result = await getCompetences(token);
	return { skills: Array.isArray(result) ? result : (result?.skills ?? []) };
};

export const setSkillEnabled = (token: string, name: string, enabled: boolean) =>
	basculerCompetence(token, name, enabled);

const normalizeField = (field: any) => {
	const key = `${field.key ?? field.name ?? ''}`;
	const isSecret = /(API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)/i.test(key);
	return {
		key,
		label: `${field.label ?? field.prompt ?? field.key ?? field.name ?? ''}`,
		default: field.default == null ? '' : `${field.default}`,
		url: field.url ?? null,
		secret: field.secret ?? isSecret,
		present: Boolean(field.present ?? field.is_set)
	};
};

const slugForProvider = (provider: any): string => {
	const name = `${provider.slug ?? provider.name ?? ''}`.toLowerCase();
	// L'abonnement Nous utilise Firecrawl en coulisses, mais c'est bien une offre Nous :
	// son identité visuelle ne doit jamais hériter du logo Firecrawl.
	if (name.includes('nous')) return 'nous';

	const backend = `${provider.web_backend ?? ''}`.toLowerCase();
	if (backend === 'brave-free') return 'brave';
	if (backend === 'ddgs') return 'duckduckgo';
	if (backend) return backend;

	if (name.includes('firecrawl')) return 'firecrawl';
	if (name.includes('duckduckgo')) return 'duckduckgo';
	if (name.includes('brave')) return 'brave';
	if (name.includes('local browser') || name.includes('chromium')) return 'chromium';
	if (name.includes('camofox')) return 'camofox';
	if (name.includes('browser use')) return 'browser-use';
	if (name.includes('browserbase')) return 'browserbase';
	if (name.includes('openai') && name.includes('codex')) return 'codex';
	if (name.includes('openai')) return 'openai';
	if (name.includes('openrouter')) return 'openrouter';
	if (name.includes('xai')) return 'xai';
	if (name.includes('fal')) return 'fal';
	if (name.includes('krea')) return 'krea';
	return name.replaceAll(/\s+/g, '-');
};

const categoryForProvider = (provider: any): 'free' | 'self_hosted' | 'paid' => {
	const badge = `${provider.category ?? provider.badge ?? ''}`.toLowerCase();
	if (badge.includes('self') || badge.includes('héberg') || badge.includes('local')) {
		return 'self_hosted';
	}
	if (
		badge.includes('free') ||
		badge.includes('gratuit') ||
		badge.includes('subscription') ||
		badge.includes('abonnement')
	) {
		return 'free';
	}
	return 'paid';
};

export const getToolConnection = async (token: string, name: string) => {
	const result = await getConfigurationOutil(token, name);
	const rawProviders = Array.isArray(result?.providers)
		? result.providers
		: Object.entries(result?.providers ?? {}).map(([providerName, value]: [string, any]) => ({
				name: providerName,
				...(value ?? {})
			}));
	return {
		note: result?.note ?? null,
		providers: rawProviders.map((provider: any) => {
			const fields = (provider.fields ?? provider.env_vars ?? []).map(normalizeField);
			const category = categoryForProvider(provider);
			const status = `${provider.status ?? ''}`.toLowerCase();
			const backend = provider.web_backend;
			return {
				name: `${provider.name ?? provider.id ?? provider.slug ?? ''}`,
				tag: provider.tag ?? provider.label ?? provider.name,
				badge: provider.badge ?? null,
				kind: provider.kind ?? (fields.length > 0 ? 'key' : 'managed'),
				fields,
				slug: slugForProvider(provider),
				advanced: provider.advanced ?? category !== 'free',
				category,
				connected: Boolean(
					provider.connected ?? provider.configured ?? provider.is_active ?? status === 'ready'
				),
				active: Boolean(
					provider.active ??
					provider.is_active ??
					(backend &&
						(backend === result?.active_search_backend ||
							backend === result?.active_extract_backend))
				)
			};
		})
	};
};

export const setToolKey = (token: string, name: string, values: Record<string, string>) =>
	enregistrerClesOutil(token, name, values);
export const testToolConnection = async (token: string, name: string) => {
	const result = await getConfigurationOutil(token, name);
	return { ok: Boolean(result?.configured), ...result };
};
export const testToolKey = async (
	_token: string,
	_name: string,
	_values: Record<string, string>
) => ({
	tested: false,
	ok: false,
	reason:
		"Hermes validera cette connexion lors de sa première utilisation. Le test n'enregistre rien."
});
export const disconnectTool = (token: string, name: string) => basculerOutil(token, name, false);
export const disconnectToolProvider = async (token: string, _name: string, keys: string[]) => {
	await Promise.all(keys.filter(Boolean).map((key) => retirerCleFournisseur(token, key)));
	invalidateToolsCache();
	return { ok: true };
};
export const startToolOAuth = async () => ({ ok: false, unavailable: true });
export const getToolOAuthStatus = async () => ({ started: false, running: false, success: false });

export const getCrawl4aiStatus = async (token: string) => {
	const servers = await getServeursMcp(token);
	const server = (servers?.servers ?? []).find((item: any) => item.name === 'crawl4ai');
	return { installed: Boolean(server), running: Boolean(server?.enabled), update_available: false };
};
export const installCrawl4ai = async (token: string) => {
	const catalog = await getCatalogueMcp(token);
	const found = (catalog?.entries ?? []).some((item: any) => item.name === 'crawl4ai');
	return found
		? installerMcp(token, 'crawl4ai', {}, true)
		: ajouterServeurMcp(token, {
				name: 'crawl4ai',
				transport: 'http',
				url: 'http://crawl4ai:11235/mcp',
				enabled: true
			});
};
export const uninstallCrawl4ai = async () => ({ ok: false, unavailable: true });
export const checkCrawl4aiUpdate = async () => ({ update_available: false });
export const startCrawl4aiUpdate = async () => ({ ok: false, unavailable: true });
export const getCrawl4aiUpdateStatus = async () => ({ running: false, success: false });
