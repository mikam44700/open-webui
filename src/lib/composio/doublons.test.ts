import { describe, expect, it } from 'vitest';

import { COUVERTURE_COMPOSIO, couvertParComposio, filtrerNatives } from './doublons';
import { CATEGORIES } from './categories';

const native = (id: string, state = 'not_connected') => ({ id, state });

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

	// Le recouvrement et la vitrine sont deux choses distinctes : Composio sait
	// faire Google Docs, Teams ou Salesforce, donc leurs cartes natives doivent
	// disparaitre — meme si Mike a choisi de ne pas les mettre en vitrine. Lier
	// les deux effacerait le recouvrement a chaque fois qu'on raccourcit la
	// liste visible, et les doublons reviendraient sans qu'on comprenne pourquoi.
	it('couvre plus large que la vitrine', () => {
		const vitrine = new Set(CATEGORIES.flatMap((c) => c.applications));
		const couverts = new Set(Object.values(COUVERTURE_COMPOSIO).flat());
		const horsVitrine = [...couverts].filter((slug) => !vitrine.has(slug));
		expect(horsVitrine.length).toBeGreaterThan(0);
	});
});
