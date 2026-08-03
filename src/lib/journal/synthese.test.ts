import { describe, expect, it } from 'vitest';

import {
	COMPTEURS_VIDES,
	alerteJournal,
	etatAffichage,
	tauxAboutis,
	tonDeStatut,
	tuiles,
	type Compteurs
} from './synthese';

const compteurs = (partiel: Partial<Compteurs>): Compteurs => {
	const base = { ...COMPTEURS_VIDES, ...partiel };
	return { ...base, total: base.ok + base.pending + base.error + base.unknown };
};

describe('tonDeStatut', () => {
	it('ne colore rien quand le compteur est a zero', () => {
		for (const statut of ['ok', 'pending', 'error', 'unknown'] as const) {
			expect(tonDeStatut(statut, 0)).toBe('neutre');
		}
	});

	it("traite l'attente comme un geste a faire, pas comme une avarie", () => {
		expect(tonDeStatut('pending', 3)).toBe('attention');
		expect(tonDeStatut('pending', 3)).not.toBe('probleme');
	});

	it('ne presente jamais un etat inconnu comme un probleme', () => {
		expect(tonDeStatut('unknown', 12)).toBe('neutre');
	});

	it("reserve le ton d'alerte aux echecs reels", () => {
		expect(tonDeStatut('error', 1)).toBe('probleme');
	});
});

describe('tuiles', () => {
	it('rend les quatre statuts dans un ordre stable', () => {
		expect(tuiles(COMPTEURS_VIDES).map((t) => t.statut)).toEqual([
			'ok',
			'pending',
			'error',
			'unknown'
		]);
	});

	it('reporte les valeurs telles quelles', () => {
		const resultat = tuiles(compteurs({ ok: 7, pending: 2, error: 1, unknown: 4 }));
		expect(resultat.map((t) => t.valeur)).toEqual([7, 2, 1, 4]);
	});
});

describe('alerteJournal', () => {
	it("n'alerte pas sur une journee entierement reussie", () => {
		expect(alerteJournal(compteurs({ ok: 20 }))).toBeNull();
	});

	it('ne dit rien quand il ne se passe rien', () => {
		expect(alerteJournal(COMPTEURS_VIDES)).toBeNull();
	});

	it('signale les echecs en priorite', () => {
		const alerte = alerteJournal(compteurs({ ok: 5, pending: 3, error: 2, unknown: 1 }));
		expect(alerte).toEqual({ gravite: 'avertissement', cle: 'journal.alerte.erreurs' });
	});

	it("n'affiche qu'une seule alerte, jamais empilee", () => {
		const alerte = alerteJournal(compteurs({ error: 2, unknown: 9, pending: 4 }));
		expect(alerte?.cle).toBe('journal.alerte.erreurs');
	});

	it("garde l'incertitude en information, pas en avertissement", () => {
		const alerte = alerteJournal(compteurs({ ok: 3, unknown: 5 }));
		expect(alerte).toEqual({ gravite: 'information', cle: 'journal.alerte.inconnus' });
	});

	it("annonce l'attente quand c'est le seul fait notable", () => {
		const alerte = alerteJournal(compteurs({ ok: 10, pending: 4 }));
		expect(alerte).toEqual({ gravite: 'information', cle: 'journal.alerte.attente' });
	});
});

describe('etatAffichage', () => {
	it('distingue une journee vide d une lecture impossible', () => {
		expect(etatAffichage(COMPTEURS_VIDES, false)).toBe('vide');
		expect(etatAffichage(null, false)).toBe('illisible');
		expect(etatAffichage(COMPTEURS_VIDES, true)).toBe('illisible');
	});

	it('affiche les donnees des qu il y a quelque chose', () => {
		expect(etatAffichage(compteurs({ ok: 1 }), false)).toBe('donnees');
	});

	it("ne fait pas passer une panne de lecture pour une journee calme", () => {
		// Le piege : sans ce test, un journal injoignable afficherait
		// tranquillement « 0 traitement », ce qui a l'air normal.
		expect(etatAffichage(compteurs({}), true)).not.toBe('vide');
	});
});

describe('tauxAboutis', () => {
	it("ne calcule rien quand aucune issue n'est connue", () => {
		expect(tauxAboutis(COMPTEURS_VIDES)).toBeNull();
		expect(tauxAboutis(compteurs({ unknown: 8 }))).toBeNull();
	});

	it("exclut l'inconnu du calcul plutot que de le compter comme un echec", () => {
		// 9 ok, 1 error, 90 unknown : le taux porte sur les 10 issues connues.
		expect(tauxAboutis(compteurs({ ok: 9, error: 1, unknown: 90 }))).toBe(90);
	});

	it("compte l'attente comme aboutie : le dossier est pret", () => {
		expect(tauxAboutis(compteurs({ ok: 5, pending: 5 }))).toBe(100);
	});

	it('rend 0 seulement quand tout ce qu on connait a echoue', () => {
		expect(tauxAboutis(compteurs({ error: 4 }))).toBe(0);
	});
});
