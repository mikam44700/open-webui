import { describe, expect, it } from 'vitest';
import {
	cerveauActif,
	cerveauxDisponibles,
	comptesParFournisseur,
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
				connecte: true,
				source: undefined
			},
			{
				id: 'gpt-5.4-mini',
				titre: 'gpt-5.4-mini',
				fournisseur: 'openai-codex',
				nomFournisseur: 'OpenAI Codex',
				connecte: true,
				source: undefined
			},
			{
				id: 'gpt-4o',
				titre: 'gpt-4o',
				fournisseur: 'openai-api',
				nomFournisseur: 'OpenAI API',
				connecte: false,
				source: undefined
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

	it('retient la source declaree par le moteur', () => {
		const cerveaux = listerCerveaux({
			providers: [
				{ slug: 'moa', name: 'Mixture of Agents', models: ['default'], source: 'virtual' }
			]
		});
		expect(cerveaux[0].source).toBe('virtual');
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

/**
 * Situation reelle du 3 aout 2026 : Hermes annonce Anthropic authentifie avec
 * ses 13 modeles, alors qu'aucun compte Anthropic n'a ete branche — les jetons
 * viennent de la session de Claude Code trouvee sur la machine.
 */
const CATALOGUE_EMPRUNTE = {
	model: 'gpt-5.6-sol',
	provider: 'openai-codex',
	providers: [
		{
			slug: 'moa',
			name: 'Mixture of Agents',
			models: ['default'],
			authenticated: true,
			source: 'virtual'
		},
		{
			slug: 'anthropic',
			name: 'Anthropic',
			models: ['claude-opus-4-8', 'claude-sonnet-5'],
			authenticated: true,
			source: 'hermes'
		},
		{
			slug: 'openai-codex',
			name: 'OpenAI Codex',
			models: ['gpt-5.6-sol'],
			authenticated: true,
			source: 'hermes'
		}
	]
};

/** Reponse de `/providers/oauth` : Anthropic n'a pas de compte a lui. */
const COMPTES_EMPRUNTES = {
	providers: [
		{ id: 'anthropic', name: 'Anthropic', status: { logged_in: false, source: null } },
		{
			id: 'claude-code',
			name: 'Claude Code',
			status: { logged_in: true, source: 'claude_code_cli' }
		},
		{ id: 'openai-codex', name: 'OpenAI OAuth (ChatGPT)', status: { logged_in: true } }
	]
};

describe('comptesParFournisseur', () => {
	it('lit l_etat de connexion de chaque compte', () => {
		expect(comptesParFournisseur(COMPTES_EMPRUNTES)).toEqual({
			anthropic: false,
			'claude-code': true,
			'openai-codex': true
		});
	});

	it('rend un objet vide plutot que de jeter quand la route ne repond pas', () => {
		expect(comptesParFournisseur(null)).toEqual({});
		expect(comptesParFournisseur({})).toEqual({});
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

	// --- Le jeton emprunte a un autre outil ---------------------------------
	//
	// Ces quatre tests tiennent ensemble une seule promesse : ce qui disparait
	// du menu ne disparait jamais a cause de son nom, et revient tout seul des
	// que le moteur declare un compte. Les casser, c'est rompre la promesse.

	const actifEmprunte = cerveauActif(CATALOGUE_EMPRUNTE);

	it('ecarte un fournisseur dont le compte est declare non connecte', () => {
		const groupes = cerveauxDisponibles(
			listerCerveaux(CATALOGUE_EMPRUNTE),
			actifEmprunte,
			comptesParFournisseur(COMPTES_EMPRUNTES)
		);
		expect(groupes.map((g) => g.fournisseur)).toEqual(['openai-codex']);
	});

	it('fait revenir le groupe des que le compte passe a connecte', () => {
		// Exactement ce que repond Hermes une fois ANTHROPIC_API_KEY posee :
		// `logged_in: true, source: "env_var"`. Aucune ligne de code a changer.
		const avecCle = {
			providers: COMPTES_EMPRUNTES.providers.map((p) =>
				p.id === 'anthropic' ? { ...p, status: { logged_in: true, source: 'env_var' } } : p
			)
		};
		const groupes = cerveauxDisponibles(
			listerCerveaux(CATALOGUE_EMPRUNTE),
			actifEmprunte,
			comptesParFournisseur(avecCle)
		);
		expect(groupes.map((g) => g.fournisseur)).toEqual(['openai-codex', 'anthropic']);
		expect(groupes[1].cerveaux.map((c) => c.id)).toEqual(['claude-opus-4-8', 'claude-sonnet-5']);
	});

	it('ecarte les agregateurs virtuels, qui ne sont pas des modeles', () => {
		const groupes = cerveauxDisponibles(listerCerveaux(CATALOGUE_EMPRUNTE), actifEmprunte);
		expect(groupes.map((g) => g.fournisseur)).not.toContain('moa');
	});

	it('ne masque rien quand la liste des comptes est indisponible', () => {
		// Route injoignable : trop montrer vaut mieux que retirer a tort un
		// fournisseur que l_utilisateur a reellement branche.
		const groupes = cerveauxDisponibles(listerCerveaux(CATALOGUE_EMPRUNTE), actifEmprunte, {});
		expect(groupes.map((g) => g.fournisseur)).toEqual(['openai-codex', 'anthropic']);
	});

	it('rend une liste vide quand rien n_est branche', () => {
		expect(cerveauxDisponibles(listerCerveaux({ providers: [] }), actif)).toEqual([]);
	});
});
