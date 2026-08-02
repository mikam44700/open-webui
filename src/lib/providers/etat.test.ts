import { describe, expect, it } from 'vitest';

import { deriverEtat, type SignauxFournisseur } from './etat';

const signaux = (partiel: Partial<SignauxFournisseur> = {}): SignauxFournisseur => ({
	aCle: true,
	cleEnregistree: false,
	compteConnecte: false,
	joignable: false,
	courant: false,
	...partiel
});

describe('deriverEtat', () => {
	it('laisse un fournisseur a cle non branche tant qu aucune cle n est enregistree', () => {
		expect(deriverEtat(signaux())).toEqual({ etat: 'not_configured', cle: false });
	});

	it('branche un fournisseur a cle des qu une cle est enregistree', () => {
		expect(deriverEtat(signaux({ cleEnregistree: true }))).toEqual({
			etat: 'configured',
			cle: true
		});
	});

	it('signale le fournisseur courant comme actif', () => {
		expect(deriverEtat(signaux({ cleEnregistree: true, courant: true }))).toEqual({
			etat: 'active',
			cle: true
		});
	});

	// Le cas Anthropic : une session Claude ouverte sur la machine rendait la carte
	// « Cle connectee » alors que le client n avait jamais saisi de cle.
	it('ne prend pas une session de compte pour une cle', () => {
		expect(deriverEtat(signaux({ compteConnecte: true, joignable: true }))).toEqual({
			etat: 'not_configured',
			cle: false
		});
	});

	it('ne prend pas la joignabilite annoncee par Hermes pour une cle', () => {
		expect(deriverEtat(signaux({ joignable: true, courant: true }))).toEqual({
			etat: 'not_configured',
			cle: false
		});
	});

	it('conserve le signal de Hermes pour un fournisseur sans cle a saisir', () => {
		expect(deriverEtat(signaux({ aCle: false, joignable: true }))).toEqual({
			etat: 'configured',
			cle: false
		});
	});

	it('conserve la session de compte pour un fournisseur sans cle a saisir', () => {
		expect(deriverEtat(signaux({ aCle: false, compteConnecte: true, courant: true }))).toEqual({
			etat: 'active',
			cle: false
		});
	});

	it('laisse un fournisseur sans cle et sans signal a l etat non branche', () => {
		expect(deriverEtat(signaux({ aCle: false }))).toEqual({ etat: 'not_configured', cle: false });
	});
});
