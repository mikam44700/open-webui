import { describe, expect, it } from 'vitest';

import {
	COUVERTURE_COMPOSIO,
	COUVERTURE_MCP,
	couvertParComposio,
	couvertParComposioEnMcp,
	filtrerNatives,
	filtrerDoublonsMcp
} from './doublons';
import { RECOMMANDEES } from './catalogue';
import { LUNARIA_MCP_CATALOG } from '$lib/utils/mcpCatalog';

const native = (id: string, state = 'not_connected') => ({ id, state });
const mcp = (name: string) => ({ name });

describe('filtrerNatives', () => {
	it('ne retire rien tant que Composio n est pas actif', () => {
		const liste = [native('google-workspace'), native('notion'), native('obsidian')];
		expect(filtrerNatives(liste, false)).toHaveLength(3);
	});

	it('retire les cartes natives que Composio porte', () => {
		const liste = [native('google-workspace'), native('microsoft-365'), native('linkedin')];
		expect(filtrerNatives(liste, true)).toEqual([]);
	});

	it('garde ce que Composio ne couvre pas', () => {
		const liste = [native('obsidian'), native('email'), native('apple'), native('hue')];
		expect(filtrerNatives(liste, true).map((i) => i.id)).toEqual([
			'obsidian',
			'email',
			'apple',
			'hue'
		]);
	});

	// Decision de Mike : aucune exception. Meme branchee, une carte que Composio
	// recouvre disparait de l'ecran.
	it('retire aussi une integration native reellement connectee', () => {
		const liste = [native('notion', 'connected'), native('obsidian', 'connected')];
		expect(filtrerNatives(liste, true).map((i) => i.id)).toEqual(['obsidian']);
	});

	it('ne garde que ce que Composio ne sait pas faire', () => {
		const liste = [
			native('google-workspace', 'connected'),
			native('notion', 'connected'),
			native('obsidian'),
			native('email'),
			native('apple'),
			native('hue')
		];
		expect(filtrerNatives(liste, true).map((i) => i.id)).toEqual([
			'obsidian',
			'email',
			'apple',
			'hue'
		]);
	});

	it('laisse la liste vide intacte', () => {
		expect(filtrerNatives([], true)).toEqual([]);
	});
});

describe('couvertParComposio', () => {
	it('reconnait un service que Composio rend', () => {
		expect(couvertParComposio('google-workspace')).toBe(true);
		expect(couvertParComposio('notion')).toBe(true);
	});

	it('laisse hors couverture ce que Composio ne peut pas atteindre', () => {
		for (const id of ['obsidian', 'email', 'apple', 'hue']) {
			expect(couvertParComposio(id)).toBe(false);
		}
	});

	it('rend faux pour un identifiant inconnu', () => {
		expect(couvertParComposio('zzz_inconnu')).toBe(false);
	});
});

describe('coherence du recouvrement', () => {
	it('ne fait pas porter le meme identifiant Composio par deux cartes natives', () => {
		const tous = Object.values(COUVERTURE_COMPOSIO).flat();
		expect(new Set(tous).size).toBe(tous.length);
	});

	it('ne declare que des identifiants exploitables', () => {
		const tous = Object.values(COUVERTURE_COMPOSIO).flat();
		for (const slug of tous) {
			expect(slug).toBe(slug.toLowerCase());
			expect(slug.trim()).not.toBe('');
		}
	});

	// Le recouvrement et la vitrine sont deux listes independantes. La vitrine
	// change au gre des choix produit ; le recouvrement, lui, decrit ce que
	// Composio sait faire. Les lier ferait revenir des doublons a chaque fois
	// qu'on raccourcit la liste visible, sans qu'on comprenne pourquoi — d'ou ces
	// deux ancrages, qui doivent tenir quelle que soit la vitrine du moment.
	it('couvre Microsoft 365 jusqu a Teams, meme si la vitrine change', () => {
		expect(COUVERTURE_COMPOSIO['microsoft-365']).toContain('microsoft_teams');
	});

	it('couvre Google Workspace au-dela de la seule messagerie', () => {
		const google = COUVERTURE_COMPOSIO['google-workspace'];
		expect(google).toContain('gmail');
		expect(google).toContain('googledrive');
		expect(google).toContain('googlecalendar');
	});
});

describe('filtrerDoublonsMcp', () => {
	it('ne retire rien tant que Composio n est pas actif', () => {
		const liste = [mcp('gmail'), mcp('notion'), mcp('data-gouv-fr')];
		expect(filtrerDoublonsMcp(liste, false)).toHaveLength(3);
	});

	// Les vedettes reelles de McpList au 3 aout 2026. Six sur sept passaient par
	// Composio : c'est le doublon qui a declenche cet arbitrage.
	it('vide la vitrine des services que Composio rend deja', () => {
		const vedettes = [
			'gmail',
			'google-calendar',
			'notion',
			'slack',
			'stripe',
			'hubspot',
			'data-gouv-fr'
		].map(mcp);
		expect(filtrerDoublonsMcp(vedettes, true).map((e) => e.name)).toEqual(['data-gouv-fr']);
	});

	// Le durcissement du 3 aout : le meme filtre porte sur le catalogue entier,
	// pas seulement sur les sept vedettes. Un doublon range dans « Tout
	// parcourir » reste un doublon.
	it('purge aussi le fond du catalogue, pas seulement la vitrine', () => {
		const catalogue = [
			'asana',
			'atlassian',
			'airtable',
			'youtube',
			'paypal',
			'quickbooks',
			'figma',
			'elevenlabs',
			'github',
			'vercel',
			'plaid',
			'comfy-cloud'
		].map(mcp);
		expect(filtrerDoublonsMcp(catalogue, true).map((e) => e.name)).toEqual([
			'plaid',
			'comfy-cloud'
		]);
	});

	it('garde les serveurs que Composio n atteint pas', () => {
		const liste = ['data-gouv-fr', 'playwright', 'n8n', 'fetch', 'canva'].map(mcp);
		expect(filtrerDoublonsMcp(liste, true)).toHaveLength(5);
	});

	it('laisse la liste vide intacte', () => {
		expect(filtrerDoublonsMcp([], true)).toEqual([]);
	});
});

describe('couvertParComposioEnMcp', () => {
	it('reconnait un serveur MCP que Composio double', () => {
		expect(couvertParComposioEnMcp('gmail')).toBe(true);
		expect(couvertParComposioEnMcp('atlassian')).toBe(true);
	});

	it('ignore la casse', () => {
		expect(couvertParComposioEnMcp('Notion')).toBe(true);
	});

	it('rend faux pour un serveur hors couverture', () => {
		for (const name of ['data-gouv-fr', 'blender', 'postgres', 'zzz_inconnu']) {
			expect(couvertParComposioEnMcp(name)).toBe(false);
		}
	});
});

describe('coherence du recouvrement MCP', () => {
	// Un slug mal orthographie ne se voit pas a l'ecran : la carte reste
	// simplement en double, sans erreur. Ce test est le seul garde-fou.
	it('ne declare que des applications qui existent au catalogue Composio', () => {
		for (const slug of Object.values(COUVERTURE_MCP).flat()) {
			expect(RECOMMANDEES.has(slug), `${slug} absent du catalogue Composio`).toBe(true);
		}
	});

	it('ne declare que des entrees qui existent au catalogue MCP', () => {
		const connus = new Set(LUNARIA_MCP_CATALOG.map((e) => e.name));
		// HubSpot est une vedette « maison » de McpList (preset mcp.hubspot.com),
		// absente du catalogue historique : elle n'en est pas moins affichee.
		const presets = new Set(['hubspot']);
		for (const name of Object.keys(COUVERTURE_MCP)) {
			expect(connus.has(name) || presets.has(name), `${name} absent du catalogue MCP`).toBe(true);
		}
	});

	it('ne fait pas porter le meme service par deux entrees MCP', () => {
		const tous = Object.values(COUVERTURE_MCP).flat();
		expect(new Set(tous).size).toBe(tous.length);
	});

	// Google est eclate cote MCP (trois serveurs) la ou il est d'un bloc cote
	// natif. Les deux tables doivent viser les memes applications Composio.
	it('couvre les trois serveurs Google de la vitrine MCP', () => {
		for (const name of ['gmail', 'google-calendar', 'google-drive']) {
			expect(couvertParComposioEnMcp(name)).toBe(true);
		}
	});
});
