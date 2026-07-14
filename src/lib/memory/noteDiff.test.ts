import { describe, it, expect } from 'vitest';
import { diffLines, hasChanges } from './noteDiff';

describe('diffLines', () => {
	it('lignes identiques → tout "same"', () => {
		const out = diffLines('a\nb\nc', 'a\nb\nc');
		expect(out).toEqual([
			{ type: 'same', text: 'a' },
			{ type: 'same', text: 'b' },
			{ type: 'same', text: 'c' }
		]);
	});

	it('ligne ajoutée → "add"', () => {
		const out = diffLines('a\nc', 'a\nb\nc');
		expect(out).toEqual([
			{ type: 'same', text: 'a' },
			{ type: 'add', text: 'b' },
			{ type: 'same', text: 'c' }
		]);
	});

	it('ligne retirée → "del"', () => {
		const out = diffLines('a\nb\nc', 'a\nc');
		expect(out).toEqual([
			{ type: 'same', text: 'a' },
			{ type: 'del', text: 'b' },
			{ type: 'same', text: 'c' }
		]);
	});

	it('mélange ajout + retrait + conservation', () => {
		const out = diffLines('titre\nvieux\nfin', 'titre\nneuf\nfin');
		expect(out).toContainEqual({ type: 'del', text: 'vieux' });
		expect(out).toContainEqual({ type: 'add', text: 'neuf' });
		expect(out).toContainEqual({ type: 'same', text: 'titre' });
		expect(out).toContainEqual({ type: 'same', text: 'fin' });
	});

	it('avant vide → tout "add"', () => {
		expect(diffLines('', 'a\nb')).toEqual([
			{ type: 'add', text: 'a' },
			{ type: 'add', text: 'b' }
		]);
	});

	it('après vide → tout "del"', () => {
		expect(diffLines('a\nb', '')).toEqual([
			{ type: 'del', text: 'a' },
			{ type: 'del', text: 'b' }
		]);
	});

	it('deux vides → aucun segment', () => {
		expect(diffLines('', '')).toEqual([]);
	});
});

describe('hasChanges', () => {
	it('contenu identique → false', () => {
		expect(hasChanges('a\nb', 'a\nb')).toBe(false);
	});

	it('différences d’espaces / lignes vides finales → false', () => {
		expect(hasChanges('a\nb  ', 'a\nb')).toBe(false);
		expect(hasChanges('a\n\n', 'a')).toBe(false);
		expect(hasChanges('a\r\nb', 'a\nb')).toBe(false);
	});

	it('contenu réellement différent → true', () => {
		expect(hasChanges('a\nb', 'a\nb\nc')).toBe(true);
		expect(hasChanges('bonjour', 'bonsoir')).toBe(true);
	});
});
