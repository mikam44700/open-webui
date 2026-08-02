import { describe, expect, it } from 'vitest';

import { RECOMMANDEES } from './catalogue';
import { DESCRIPTIONS_FR, descriptionFr } from './descriptions';

describe('libellés français du catalogue', () => {
	it('couvre toutes les applications recommandées', () => {
		const sans = [...RECOMMANDEES].filter((slug) => !descriptionFr(slug));
		expect(sans).toEqual([]);
	});

	// La carte annonce, la fenêtre développe. Une ligne qui déborde casse
	// l'alignement des cartes — c'est tout l'intérêt d'un libellé court.
	it('reste court sur chaque ligne', () => {
		for (const [slug, texte] of Object.entries(DESCRIPTIONS_FR)) {
			expect(texte.length, `${slug} : « ${texte} »`).toBeLessThanOrEqual(55);
			expect(texte.trim(), slug).not.toBe('');
		}
	});

	it('écrit en français, avec ses accents', () => {
		// Un libellé resté en anglais se repère à ces mots-là.
		const anglicismes = /\b(the|your|and|with|for|platform|allows)\b/i;
		const suspects = Object.entries(DESCRIPTIONS_FR)
			.filter(([, texte]) => anglicismes.test(texte))
			.map(([slug]) => slug);
		expect(suspects).toEqual([]);
	});

	it('ne garde pas de libellé orphelin', () => {
		const orphelins = Object.keys(DESCRIPTIONS_FR).filter((slug) => !RECOMMANDEES.has(slug));
		expect(orphelins).toEqual([]);
	});

	it('rend null hors du catalogue recommandé', () => {
		expect(descriptionFr('zzz_inconnu')).toBeNull();
	});

	it('ignore la casse', () => {
		expect(descriptionFr('GMAIL')).not.toBeNull();
	});
});
