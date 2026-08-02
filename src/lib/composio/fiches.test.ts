import { describe, expect, it } from 'vitest';

import { CATEGORIES } from './categories';
import { FICHES, ficheDe } from './fiches';

const vitrine = CATEGORIES.flatMap((c) => c.applications);

describe('fiches de la vitrine', () => {
	// Une application en vitrine sans fiche perd sa description, ses etiquettes
	// et son « Voir ce que ca fait » : sa carte devient plus courte que les
	// autres et la grille se deforme.
	it('couvre toutes les applications de la vitrine', () => {
		const sans = vitrine.filter((slug) => !ficheDe(slug));
		expect(sans).toEqual([]);
	});

	// Au-dela de trois, les etiquettes passent a la ligne et la hauteur des
	// cartes cesse d'etre uniforme — exactement ce qu'on cherche a eviter.
	it('ne depasse jamais trois etiquettes', () => {
		for (const [slug, fiche] of Object.entries(FICHES)) {
			expect(fiche.tags.length, slug).toBeLessThanOrEqual(3);
			expect(fiche.tags.length, slug).toBeGreaterThan(0);
		}
	});

	it('donne une phrase et au moins une action a chaque fiche', () => {
		for (const [slug, fiche] of Object.entries(FICHES)) {
			expect(fiche.desc.trim(), slug).not.toBe('');
			expect(fiche.actions.length, slug).toBeGreaterThan(0);
		}
	});

	// Une fiche orpheline signale une application retiree de la vitrine sans que
	// son contenu ait suivi : ce n'est pas grave a l'ecran, mais ca pourrit le
	// fichier au fil des changements de liste.
	it('ne garde pas de fiche pour une application hors vitrine', () => {
		const connues = new Set(vitrine);
		const orphelines = Object.keys(FICHES).filter((slug) => !connues.has(slug));
		expect(orphelines).toEqual([]);
	});

	it('rend null pour une application du reste du catalogue', () => {
		expect(ficheDe('zzz_application_obscure')).toBeNull();
	});

	it('trouve la fiche quelle que soit la casse', () => {
		expect(ficheDe('GMAIL')).not.toBeNull();
	});
});
