/**
 * Ce que l'onglet MCP ne montre pas.
 *
 * Le catalogue historique porte 57 entrees. Trente-quatre d'entre elles ne
 * sont pas dans Composio, mais peu meritent la place : de l'outillage de
 * developpeur, des logiciels de creation qu'il faut avoir ouverts sur sa
 * machine, des services financiers de niche.
 *
 * Tri fait avec Mike le 3 aout 2026, section par section. Rien n'est efface
 * du catalogue : c'est un voile, pas une suppression. Retirer une ligne d'ici
 * suffit a faire revenir l'entree, avec sa categorie et sa visibilite d'avant.
 *
 * Ce voile s'applique a `allEntries`, apres la fusion catalogue + moteur. Le
 * filtrer plus tot ne suffirait pas : Hermes livre `blender`, `n8n` et
 * `unreal-engine` dans ses propres manifests, et le code reinjecte toute
 * entree du moteur absente du catalogue historique — les exclus reviendraient
 * ranges en « autre », sans categorie ni libelle.
 *
 * Ecarter de l'ecran n'est pas desinstaller : ces serveurs restent
 * installables cote moteur avec `hermes mcp install <nom>`.
 */
export const MCP_EXCLUS: Record<string, string> = {
	// Finance — seul Plaid est retenu (agregation de comptes bancaires).
	alpaca: 'courtage boursier, hors sujet pour un dirigeant',
	'polygon-io': 'donnees de marche boursier, usage de niche',
	dune: 'analyse de donnees blockchain',
	tradingview: 'analyse technique graphique',

	// Creation — Canva et Higgsfield restent, le reste demande un logiciel
	// ouvert sur la machine du client.
	blender: 'exige une session Blender ouverte (MCP natif Hermes)',
	'meigen-ai-design': 'generateur de design redondant avec Canva',
	ableton: 'exige Ableton Live ouvert sur la machine',
	'davinci-resolve': 'exige DaVinci Resolve ouvert sur la machine',

	// Recherche — Brave vit dans l'onglet « Recherche & web », avec Exa et
	// Tavily. Deux portes vers le meme service, c'est le doublon qu'on chasse.
	'brave-search': 'deja present dans l’onglet Recherche & web',

	// Developpement — n8n et Playwright restent, le reste est de l'outillage
	// que seul un developpeur branche.
	git: 'outillage de developpeur',
	kubernetes: 'outillage d’infrastructure',
	context7: 'documentation de librairies, usage de developpeur',
	puppeteer: 'fait doublon avec Playwright, garde lui',

	// Bases de donnees — la section entiere. Supabase et Neon font doublon avec
	// Composio ; les trois autres sont des connexions SQL directes, de
	// l'outillage de developpeur qu'aucun client ne branche.
	supabase: 'deja porte par Composio',
	neon: 'deja porte par Composio',
	postgres: 'connexion SQL directe, outillage de developpeur',
	redis: 'cache technique, outillage de developpeur',
	sqlite: 'fichier de base local, outillage de developpeur',

	// Crypto — la section entiere. Aucun dirigeant a qui LunarIA s'adresse ne
	// branche un portefeuille blockchain sur son assistant.
	base: 'blockchain, hors cible',
	ccxt: 'places de marche crypto, hors cible',
	coingecko: 'cours des cryptomonnaies, hors cible',
	etherscan: 'explorateur Ethereum, hors cible',
	'solana-agent-kit': 'portefeuille Solana, hors cible',
	'the-graph': 'indexation blockchain, hors cible',
	thirdweb: 'developpement web3, hors cible',

	// Autre
	'unreal-engine': 'exige l’editeur Unreal ouvert (MCP natif Hermes)'
};

/** Entree du catalogue MCP, reduite a ce dont le voile a besoin. */
export type EntreeCatalogue = {
	name: string;
};

/** Cette entree est-elle ecartee de l'onglet ? */
export const estExclu = (name: string): boolean =>
	Object.prototype.hasOwnProperty.call(MCP_EXCLUS, `${name}`.toLowerCase());

/**
 * Retire du catalogue ce que Mike a ecarte.
 *
 * A appliquer sur le catalogue complet, jamais sur les connecteurs installes :
 * on ne cache pas ce qui tourne deja chez le client.
 */
export const filtrerCatalogueMcp = <T extends EntreeCatalogue>(entrees: T[]): T[] =>
	entrees.filter((entree) => !estExclu(entree.name));
