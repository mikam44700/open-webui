// Catalogue MCP historique de LunarIA.
//
// Hermes V2 ne renvoie actuellement que les quelques manifests livrés avec son dépôt.
// LunarIA V1 complétait ce catalogue avec le registre curé de 55 connecteurs, puis Linear,
// Blender, n8n et Unreal Engine fournis par Hermes (deux d'entre eux sont propres au moteur).
// Cette liste locale garde l'union de 57 entrées, le rangement et la visibilité de la V1 même
// si le registre distant est indisponible. Les serveurs HTTP officiels restent connectables
// directement ; les connecteurs stdio absents de Hermes V2 sont montrés sans faux bouton.

export type LunarMcpCatalogEntry = {
	name: string;
	transport: 'stdio' | 'http' | 'sse';
	auth_type: 'none' | 'key' | 'oauth';
	installed: boolean;
	category: string;
	visibility: 'visible' | 'expert';
	installable: boolean;
	preset?: {
		transport: 'http' | 'sse';
		url: string;
		auth_type: 'none' | 'key' | 'oauth';
	};
};

const VISIBLE: Record<string, string[]> = {
	productivity: [
		'gmail',
		'google-calendar',
		'google-drive',
		'notion',
		'slack',
		'asana',
		'linear',
		'atlassian',
		'airtable',
		'youtube'
	],
	finance: ['stripe', 'paypal', 'quickbooks', 'plaid'],
	// comfy-cloud est livré par Hermes (optional-mcps/comfy-cloud) mais manquait
	// ici : il tombait donc en catégorie « autre », visibilité experte, invisible
	// pour le client. Or c'est de la génération d'images, de vidéo et de 3D en
	// connexion par compte, sans rien à installer — sa place est en vitrine.
	creation: ['canva', 'figma', 'elevenlabs', 'higgsfield', 'comfy-cloud'],
	search: ['brave-search']
};

const EXPERT: Record<string, string[]> = {
	finance: ['alpaca', 'polygon-io', 'dune', 'tradingview'],
	creation: ['meigen-ai-design', 'blender', 'ableton', 'davinci-resolve'],
	devops: [
		'github',
		'git',
		'docker-hub',
		'kubernetes',
		'cloudflare',
		'vercel',
		'sentry',
		'context7',
		'playwright',
		'puppeteer',
		'n8n'
	],
	database: ['postgres', 'supabase', 'neon', 'redis', 'sqlite'],
	crypto: ['base', 'ccxt', 'coingecko', 'etherscan', 'solana-agent-kit', 'the-graph', 'thirdweb'],
	tools: ['fetch', 'memory', 'sequential-thinking', 'filesystem', 'aws', 'mistral'],
	other: ['unreal-engine']
};

const KEY_AUTH = new Set([
	'airtable',
	'alpaca',
	'brave-search',
	'dune',
	'elevenlabs',
	'etherscan',
	'filesystem',
	'github',
	'mistral',
	'notion',
	'paypal',
	'polygon-io',
	'postgres',
	'quickbooks',
	'redis',
	'slack',
	'solana-agent-kit',
	'sqlite',
	'thirdweb'
]);

// Serveurs distants officiels du registre LunarIA V1, épinglé le 09/07/2026.
// Ceux-ci sont réellement ajoutables par l'API Hermes actuelle, contrairement aux entrées
// stdio dont le manifest n'est pas encore livré par Hermes V2.
const REMOTE: Record<string, string> = {
	asana: 'https://mcp.asana.com/v2/mcp',
	atlassian: 'https://mcp.atlassian.com/v1/mcp/authv2',
	base: 'https://mcp.base.org',
	canva: 'https://mcp.canva.com/mcp',
	cloudflare: 'https://mcp.cloudflare.com/mcp',
	coingecko: 'https://mcp.api.coingecko.com/sse',
	// URL du manifest Hermes (optional-mcps/comfy-cloud/manifest.yaml) :
	// Streamable HTTP + OAuth 2.1 natif, rien à installer localement.
	'comfy-cloud': 'https://cloud.comfy.org/mcp',
	context7: 'https://mcp.context7.com/mcp',
	figma: 'http://127.0.0.1:3845/mcp',
	higgsfield: 'https://mcp.higgsfield.ai',
	linear: 'https://mcp.linear.app/sse',
	neon: 'https://mcp.neon.tech/mcp',
	plaid: 'https://api.dashboard.plaid.com/mcp/sse',
	sentry: 'https://mcp.sentry.dev/mcp',
	stripe: 'https://mcp.stripe.com',
	supabase: 'https://mcp.supabase.com/mcp',
	'the-graph': 'https://token-api.mcp.thegraph.com/sse',
	vercel: 'https://mcp.vercel.com'
};

const entry = (
	name: string,
	category: string,
	visibility: 'visible' | 'expert'
): LunarMcpCatalogEntry => {
	const url = REMOTE[name];
	const transport = url?.includes('/sse') || url?.endsWith('/sse') ? 'sse' : url ? 'http' : 'stdio';
	const authType = name === 'figma' ? 'none' : url ? 'oauth' : KEY_AUTH.has(name) ? 'key' : 'none';
	return {
		name,
		transport,
		auth_type: authType,
		installed: false,
		category,
		visibility,
		installable: Boolean(url),
		...(url
			? {
					preset: {
						transport: transport === 'sse' ? ('sse' as const) : ('http' as const),
						url,
						auth_type: authType
					}
				}
			: {})
	};
};

export const LUNARIA_MCP_CATALOG: LunarMcpCatalogEntry[] = [
	...Object.entries(VISIBLE).flatMap(([category, names]) =>
		names.map((name) => entry(name, category, 'visible'))
	),
	...Object.entries(EXPERT).flatMap(([category, names]) =>
		names.map((name) => entry(name, category, 'expert'))
	)
];
