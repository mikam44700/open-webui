import { describe, expect, it } from 'vitest';
import {
	cerveauActif,
	cerveauxDisponibles,
	estActif,
	listerCerveaux,
	type Cerveau
} from './cerveaux';

/** Reponse reelle du moteur, abregee : deux fournisseurs, un seul branche. */
const CATALOGUE = {
	model: 'gpt-5.6-sol',
	provider: 'openai-codex',
	providers: [
		{
			slug: 'nous',
			name: 'Nous Portal',
			models: [],
			authenticated: false
		},
		{
			slug: 'openai-codex',
			name: 'OpenAI Codex',
			models: ['gpt-5.6-sol', 'gpt-5.4-mini'],
			authenticated: true
		},
		{
			slug: 'openai-api',
			name: 'OpenAI API',
			models: ['gpt-4o'],
			authenticated: false
		}
	]
};

describe('listerCerveaux', () => {
	it('met a plat la forme par fournisseurs', () => {
		expect(listerCerveaux(CATALOGUE)).toEqual([
			{
				id: 'gpt-5.6-sol',
				titre: 'gpt-5.6-sol',
				fournisseur: 'openai-codex',
				nomFournisseur: 'OpenAI Codex',
				connecte: true
			},
			{
				id: 'gpt-5.4-mini',
				titre: 'gpt-5.4-mini',
				fournisseur: 'openai-codex',
				nomFournisseur: 'OpenAI Codex',
				connecte: true
			},
			{
				id: 'gpt-4o',
				titre: 'gpt-4o',
				fournisseur: 'openai-api',
				nomFournisseur: 'OpenAI API',
				connecte: false
			}
		]);
	});

	it('accepte un tableau de chaines', () => {
		expect(listerCerveaux(['a', 'b'])).toEqual([
			{ id: 'a', titre: 'a', connecte: true },
			{ id: 'b', titre: 'b', connecte: true }
		]);
	});

	it('accepte un objet indexe par fournisseur', () => {
		expect(listerCerveaux({ ollama: ['llama3'] })).toEqual([
			{ id: 'llama3', titre: 'llama3', fournisseur: 'ollama', connecte: true }
		]);
	});

	it('rend une liste vide plutot que de jeter sur une reponse absente', () => {
		expect(listerCerveaux(null)).toEqual([]);
		expect(listerCerveaux(undefined)).toEqual([]);
		expect(listerCerveaux({ providers: [] })).toEqual([]);
	});

	it('ignore les entrees sans identifiant', () => {
		expect(listerCerveaux({ providers: [{ slug: 'x', name: 'X', models: ['', {}] }] })).toEqual([]);
	});
});

describe('cerveauActif', () => {
	it('lit le couple declare par le moteur', () => {
		expect(cerveauActif(CATALOGUE)).toEqual({
			modele: 'gpt-5.6-sol',
			fournisseur: 'openai-codex'
		});
	});

	it('rend null plutot que de deviner quand le moteur ne dit rien', () => {
		expect(cerveauActif({})).toEqual({ modele: null, fournisseur: null });
	});
});

describe('estActif', () => {
	const actif = { modele: 'gpt-5.6-sol', fournisseur: 'openai-codex' };

	it('exige le nom ET le fournisseur', () => {
		const bon: Cerveau = {
			id: 'gpt-5.6-sol',
			titre: 'gpt-5.6-sol',
			fournisseur: 'openai-codex',
			connecte: true
		};
		expect(estActif(bon, actif)).toBe(true);
		expect(estActif({ ...bon, fournisseur: 'autre' }, actif)).toBe(false);
		expect(estActif({ ...bon, id: 'gpt-5.4-mini' }, actif)).toBe(false);
	});

	it('tolere un fournisseur absent des deux cotes', () => {
		const sansFournisseur: Cerveau = { id: 'gpt-5.6-sol', titre: 'gpt-5.6-sol', connecte: true };
		expect(estActif(sansFournisseur, actif)).toBe(true);
	});
});

describe('cerveauxDisponibles', () => {
	const actif = cerveauActif(CATALOGUE);

	it('ecarte les fournisseurs sans compte branche', () => {
		const groupes = cerveauxDisponibles(listerCerveaux(CATALOGUE), actif);
		expect(groupes.map((g) => g.fournisseur)).toEqual(['openai-codex']);
		expect(groupes[0].cerveaux.map((c) => c.id)).toEqual(['gpt-5.6-sol', 'gpt-5.4-mini']);
	});

	it('place le fournisseur actif en tete', () => {
		const cerveaux: Cerveau[] = [
			{
				id: 'a',
				titre: 'a',
				fournisseur: 'anthropic',
				nomFournisseur: 'Anthropic',
				connecte: true
			},
			{
				id: 'b',
				titre: 'b',
				fournisseur: 'openai-codex',
				nomFournisseur: 'OpenAI Codex',
				connecte: true
			}
		];
		expect(cerveauxDisponibles(cerveaux, actif).map((g) => g.fournisseur)).toEqual([
			'openai-codex',
			'anthropic'
		]);
	});

	it('rend une liste vide quand rien n_est branche', () => {
		expect(cerveauxDisponibles(listerCerveaux({ providers: [] }), actif)).toEqual([]);
	});
});
