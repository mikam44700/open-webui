import { describe, expect, it } from 'vitest';

import { MCP_EXCLUS, estExclu, filtrerCatalogueMcp } from './exclusions';
import { LUNARIA_MCP_CATALOG } from '$lib/utils/mcpCatalog';

const e = (name: string) => ({ name });

describe('filtrerCatalogueMcp', () => {
	it('retire les entrees ecartees', () => {
		const liste = [e('plaid'), e('alpaca'), e('canva'), e('blender')];
		expect(filtrerCatalogueMcp(liste).map((x) => x.name)).toEqual(['plaid', 'canva']);
	});

	it('laisse passer ce qui n est pas ecarte', () => {
		const liste = [e('plaid'), e('canva'), e('higgsfield'), e('n8n'), e('playwright')];
		expect(filtrerCatalogueMcp(liste)).toHaveLength(5);
	});

	it('laisse la liste vide intacte', () => {
		expect(filtrerCatalogueMcp([])).toEqual([]);
	});
});

describe('estExclu', () => {
	it('ignore la casse', () => {
		expect(estExclu('Brave-Search')).toBe(true);
	});

	it('rend faux pour une entree inconnue', () => {
		expect(estExclu('zzz_inconnu')).toBe(false);
	});
});

describe('les choix de la section Finance', () => {
	it('garde Plaid', () => expect(estExclu('plaid')).toBe(false));

	it('ecarte le reste', () => {
		for (const n of ['alpaca', 'polygon-io', 'dune', 'tradingview']) {
			expect(estExclu(n)).toBe(true);
		}
	});
});

describe('les choix de la section Creation', () => {
	it('garde Canva et Higgsfield', () => {
		expect(estExclu('canva')).toBe(false);
		expect(estExclu('higgsfield')).toBe(false);
	});

	it('ecarte ce qui exige un logiciel ouvert sur la machine', () => {
		for (const n of ['blender', 'ableton', 'davinci-resolve', 'meigen-ai-design']) {
			expect(estExclu(n)).toBe(true);
		}
	});
});

describe('les choix de la section Developpement', () => {
	it('garde n8n et Playwright', () => {
		expect(estExclu('n8n')).toBe(false);
		expect(estExclu('playwright')).toBe(false);
	});

	it('ecarte le reste, Puppeteer compris', () => {
		for (const n of ['git', 'kubernetes', 'context7', 'puppeteer']) {
			expect(estExclu(n)).toBe(true);
		}
	});
});

// Brave vit dans « Recherche & web » avec Exa et Tavily. Le remettre ici
// recreerait exactement le doublon qu'on est en train de retirer.
it('ecarte Brave Search, qui appartient a l onglet Recherche & web', () => {
	expect(estExclu('brave-search')).toBe(true);
});

// La section bases de donnees part en entier : Supabase et Neon parce que
// Composio les porte, les trois autres parce qu'aucun client ne branche une
// connexion SQL sur son assistant.
describe('les choix de la section Bases de donnees', () => {
	it('ecarte les cinq entrees', () => {
		for (const n of ['supabase', 'neon', 'postgres', 'redis', 'sqlite']) {
			expect(estExclu(n)).toBe(true);
		}
	});
});

// La section crypto part en entier : rien de ce qui touche aux portefeuilles,
// aux places de marche ou aux explorateurs de chaine ne doit revenir a l'ecran.
describe('les choix de la section Crypto', () => {
	it('ecarte les sept entrees', () => {
		for (const n of [
			'base',
			'ccxt',
			'coingecko',
			'etherscan',
			'solana-agent-kit',
			'the-graph',
			'thirdweb'
		]) {
			expect(estExclu(n)).toBe(true);
		}
	});
});

// Non mentionnes par Mike le 3 aout : ils restent au catalogue, en mode
// « Reglages avances » comme avant. Ce test fige ce statu quo pour qu'une
// disparition silencieuse se voie.
describe('sections laissees en l etat', () => {
	it('garde les outils systeme', () => {
		for (const n of ['fetch', 'memory', 'sequential-thinking', 'filesystem', 'aws']) {
			expect(estExclu(n)).toBe(false);
		}
	});
});

describe('coherence du voile', () => {
	// Un nom mal orthographie n'ecarte rien et ne leve aucune erreur : l'entree
	// resterait simplement a l'ecran. Ce test est le seul garde-fou.
	it('ne nomme que des entrees qui existent au catalogue', () => {
		const connus = new Set(LUNARIA_MCP_CATALOG.map((x) => x.name));
		for (const name of Object.keys(MCP_EXCLUS)) {
			expect(connus.has(name), `${name} absent du catalogue MCP`).toBe(true);
		}
	});

	it('justifie chaque exclusion', () => {
		for (const [name, raison] of Object.entries(MCP_EXCLUS)) {
			expect(raison.trim(), `${name} sans justification`).not.toBe('');
		}
	});

	it('ecarte vingt-six entrees', () => {
		expect(Object.keys(MCP_EXCLUS)).toHaveLength(26);
	});
});
