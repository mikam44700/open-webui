import { describe, expect, it } from 'vitest';

import { RECOMMANDEES } from './catalogue';
import { FICHES } from './fiches';
import { FICHES_CATALOGUE, ficheCatalogueDe } from './fiches-catalogue';

const couvertes = new Set([...Object.keys(FICHES), ...Object.keys(FICHES_CATALOGUE)]);

describe('fiches du catalogue recommandé', () => {
	// Sans fiche, « Voir ce que ça fait » retombe sur le texte anglais de
	// Composio — dans un produit vendu en français.
	it('couvre les 318 applications recommandées', () => {
		const sans = [...RECOMMANDEES].filter((slug) => !couvertes.has(slug));
		expect(sans).toEqual([]);
	});

	it('ne double jamais une fiche de vitrine', () => {
		const doublons = Object.keys(FICHES_CATALOGUE).filter((slug) => slug in FICHES);
		expect(doublons).toEqual([]);
	});

	it('tient trois étiquettes et au moins deux actions', () => {
		for (const [slug, fiche] of Object.entries(FICHES_CATALOGUE)) {
			expect(fiche.tags.length, slug).toBeLessThanOrEqual(3);
			expect(fiche.tags.length, slug).toBeGreaterThan(0);
			expect(fiche.actions.length, slug).toBeGreaterThanOrEqual(2);
		}
	});

	it('reste en français', () => {
		const anglicismes = /\b(the|your|and|with|for|allows|platform)\b/i;
		const suspects = Object.entries(FICHES_CATALOGUE)
			.filter(([, f]) => [...f.tags, ...f.actions].some((s) => anglicismes.test(s)))
			.map(([slug]) => slug);
		expect(suspects).toEqual([]);
	});

	it('ne garde pas de fiche orpheline', () => {
		const orphelines = Object.keys(FICHES_CATALOGUE).filter((slug) => !RECOMMANDEES.has(slug));
		expect(orphelines).toEqual([]);
	});

	it('rend null hors du catalogue', () => {
		expect(ficheCatalogueDe('zzz_inconnu')).toBeNull();
	});
});
