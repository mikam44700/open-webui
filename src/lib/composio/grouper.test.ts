import { describe, expect, it } from 'vitest';

import { CATEGORIES } from './categories';
import { filtrer, grouper, horsCategories, normaliser } from './grouper';
import type { ApplicationAffichee } from './etat';

const app = (
	slug: string,
	nom: string,
	etat: ApplicationAffichee['etat'] = 'non_connectee'
): ApplicationAffichee => ({ slug, nom, etat, connexionId: etat === 'connectee' ? 'c1' : null });

describe('normaliser', () => {
	it('ignore la casse et les accents', () => {
		expect(normaliser('Réseaux Sociaux')).toBe('reseaux sociaux');
		expect(normaliser('  Agenda  ')).toBe('agenda');
	});
});

describe('filtrer', () => {
	const catalogue = [
		app('gmail', 'Gmail'),
		app('googlecalendar', 'Google Calendar'),
		app('1password', '1Password')
	];

	it('rend tout quand la recherche est vide', () => {
		expect(filtrer(catalogue, '')).toHaveLength(3);
		expect(filtrer(catalogue, '   ')).toHaveLength(3);
	});

	it('trouve sur le nom d origine', () => {
		expect(filtrer(catalogue, 'gmail').map((a) => a.slug)).toEqual(['gmail']);
	});

	// Le nom francais est le seul ou « agenda » apparait.
	it('trouve sur le nom francais', () => {
		expect(filtrer(catalogue, 'agenda').map((a) => a.slug)).toEqual(['googlecalendar']);
	});

	it('trouve sur l identifiant', () => {
		expect(filtrer(catalogue, '1password').map((a) => a.slug)).toEqual(['1password']);
	});

	it('cherche dans tout le catalogue, y compris hors categories', () => {
		const hors = [app('zzz_obscure', 'Application obscure')];
		expect(filtrer(hors, 'obscure')).toHaveLength(1);
	});
});

describe('grouper', () => {
	it('met les connectees en premier, dans leur propre section', () => {
		const sections = grouper([app('gmail', 'Gmail', 'connectee'), app('slack', 'Slack')]);
		expect(sections[0].id).toBe('connectees');
		expect(sections[0].applications.map((a) => a.slug)).toEqual(['gmail']);
	});

	// Sinon Gmail apparaitrait deux fois : en haut et dans sa categorie.
	it('ne repete pas une application connectee dans sa categorie', () => {
		const sections = grouper([app('gmail', 'Gmail', 'connectee')]);
		expect(sections).toHaveLength(1);
		expect(sections[0].id).toBe('connectees');
	});

	it('range chaque application dans sa categorie', () => {
		const sections = grouper([app('gmail', 'Gmail'), app('stripe', 'Stripe')]);
		expect(sections.map((s) => s.id)).toEqual(['messagerie', 'compta']);
	});

	it('respecte l ordre des categories', () => {
		const sections = grouper([app('github', 'GitHub'), app('gmail', 'Gmail')]);
		expect(sections.map((s) => s.id)).toEqual(['messagerie', 'developpement']);
	});

	it('ne rend jamais une section vide', () => {
		expect(grouper([])).toEqual([]);
		expect(grouper([app('zzz_obscure', 'Obscure')])).toEqual([]);
	});

	it('ignore la casse de l identifiant', () => {
		const sections = grouper([app('GMAIL', 'Gmail')]);
		expect(sections[0].id).toBe('messagerie');
	});
});

describe('horsCategories', () => {
	it('garde ce qui n est ni connecte ni range', () => {
		const reste = horsCategories([
			app('gmail', 'Gmail'),
			app('zzz_obscure', 'Obscure'),
			app('slack', 'Slack', 'connectee')
		]);
		expect(reste.map((a) => a.slug)).toEqual(['zzz_obscure']);
	});
});

describe('catalogue cure', () => {
	it('ne declare pas deux fois la meme application', () => {
		const tous = CATEGORIES.flatMap((c) => c.applications);
		expect(new Set(tous).size).toBe(tous.length);
	});

	it('n a pas de categorie vide', () => {
		for (const categorie of CATEGORIES) {
			expect(categorie.applications.length).toBeGreaterThan(0);
		}
	});
});
