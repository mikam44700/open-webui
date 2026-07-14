import { describe, it, expect } from 'vitest';
import { buildFolderList, buildSuggestPrompt, parseSuggestions } from './suggestFiling';
import type { MemoryNode } from '$lib/apis/memory';

const folders = [
	{ path: '01-Projets', label: 'En cours' },
	{ path: '02-Domaines', label: 'Mon activité' },
	{ path: '02-Domaines/Clients', label: 'Clients' },
	{ path: 'Personnes', label: 'Personnes' }
];

const wrap = (options: Array<{ folder: string; reason: string }>, notePath = '00-Réception/n.md') =>
	JSON.stringify({ suggestions: [{ notePath, options }] });

describe('buildFolderList', () => {
	it('aplatit les dossiers et exclut la Réception', () => {
		const tree: MemoryNode[] = [
			{ name: '00-Réception', path: '00-Réception', type: 'folder', children: [] },
			{
				name: '02-Domaines',
				path: '02-Domaines',
				type: 'folder',
				children: [{ name: 'Clients', path: '02-Domaines/Clients', type: 'folder', children: [] }]
			},
			{ name: 'note', path: 'note.md', type: 'note', children: [] }
		];
		const out = buildFolderList(tree);
		expect(out.map((f) => f.path)).toEqual(['02-Domaines', '02-Domaines/Clients']);
	});

	it('applique le libellé lisible fourni', () => {
		const tree: MemoryNode[] = [
			{ name: '02-Domaines', path: '02-Domaines', type: 'folder', children: [] }
		];
		const out = buildFolderList(tree, (name) => (name === '02-Domaines' ? 'Mon activité' : name));
		expect(out[0].label).toBe('Mon activité');
	});
});

describe('buildSuggestPrompt', () => {
	it('inclut les dossiers cibles, le contenu de la note et une exigence JSON', () => {
		const prompt = buildSuggestPrompt(
			[{ path: '00-Réception/n.md', content: 'Échange avec Acme' }],
			folders
		);
		expect(prompt).toContain('Personnes');
		expect(prompt).toContain('Acme');
		expect(prompt.toLowerCase()).toContain('json');
	});
});

describe('parseSuggestions', () => {
	it('parse un JSON valide et classe les options', () => {
		const raw = wrap([
			{ folder: 'Personnes', reason: 'client' },
			{ folder: '01-Projets', reason: 'projet' }
		]);
		const out = parseSuggestions(raw, folders);
		expect(out).toHaveLength(1);
		expect(out[0].notePath).toBe('00-Réception/n.md');
		expect(out[0].suggestions.map((s) => s.folder)).toEqual(['Personnes', '01-Projets']);
		expect(out[0].suggestions[0].rank).toBe(1);
		expect(out[0].suggestions[0].label).toBe('Personnes');
		expect(out[0].suggestions[1].label).toBe('En cours');
	});

	it('rejette un dossier absent de l’arbre', () => {
		const raw = wrap([
			{ folder: 'Inexistant', reason: 'x' },
			{ folder: 'Personnes', reason: 'ok' }
		]);
		const out = parseSuggestions(raw, folders);
		expect(out[0].suggestions.map((s) => s.folder)).toEqual(['Personnes']);
	});

	it('exclut 00-Réception comme destination', () => {
		const raw = wrap([{ folder: '00-Réception', reason: 'non' }]);
		const out = parseSuggestions(raw, folders);
		expect(out[0].suggestions).toHaveLength(0);
	});

	it('plafonne à 3 options et re-classe', () => {
		const raw = wrap([
			{ folder: 'Personnes', reason: 'a' },
			{ folder: '01-Projets', reason: 'b' },
			{ folder: '02-Domaines', reason: 'c' },
			{ folder: '02-Domaines/Clients', reason: 'd' }
		]);
		const out = parseSuggestions(raw, folders);
		expect(out[0].suggestions).toHaveLength(3);
		expect(out[0].suggestions.map((s) => s.rank)).toEqual([1, 2, 3]);
	});

	it('déduplique par dossier', () => {
		const raw = wrap([
			{ folder: 'Personnes', reason: 'a' },
			{ folder: 'Personnes', reason: 'b' }
		]);
		const out = parseSuggestions(raw, folders);
		expect(out[0].suggestions).toHaveLength(1);
	});

	it('accepte un libellé lisible à la place du chemin', () => {
		const raw = wrap([{ folder: 'Mon activité', reason: 'dossier métier' }]);
		const out = parseSuggestions(raw, folders);
		expect(out[0].suggestions[0].folder).toBe('02-Domaines');
	});

	it('extrait le JSON même entouré de texte', () => {
		const raw = 'Voici mes suggestions : ' + wrap([{ folder: 'Personnes', reason: 'ok' }]) + ' merci';
		const out = parseSuggestions(raw, folders);
		expect(out[0].suggestions[0].folder).toBe('Personnes');
	});

	it('réponse non-JSON ou vide → aucune suggestion', () => {
		expect(parseSuggestions('pas du json du tout', folders)).toEqual([]);
		expect(parseSuggestions('', folders)).toEqual([]);
	});

	it('conserve la justification (reason) de chaque option', () => {
		const raw = wrap([{ folder: 'Personnes', reason: 'La note décrit un échange client.' }]);
		const out = parseSuggestions(raw, folders);
		expect(out[0].suggestions[0].reason).toBe('La note décrit un échange client.');
	});

	it('note sans option fiable → tableau de suggestions vide (pas d’erreur)', () => {
		const raw = wrap([{ folder: 'Inexistant', reason: 'x' }]);
		const out = parseSuggestions(raw, folders);
		expect(out[0].suggestions).toEqual([]);
	});
});
