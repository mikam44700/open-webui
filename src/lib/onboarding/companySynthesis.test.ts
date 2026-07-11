import { describe, it, expect } from 'vitest';
import {
	parseSynthesis,
	isContextEmpty,
	formatContextForProfile,
	buildSynthesisUserContent,
	EMPTY_CONTEXT,
	type CompanyContext
} from './companySynthesis';

describe('parseSynthesis — jamais inventer, normaliser honnêtement', () => {
	it('parse un JSON propre en CompanyContext', () => {
		const raw = JSON.stringify({
			offre: 'Logiciel de gestion pour dentistes',
			tonDeMarque: 'chaleureux, direct',
			clienteleCible: 'cabinets dentaires',
			services: ['prise de rendez-vous', 'facturation', 'facturation']
		});
		const ctx = parseSynthesis(raw);
		expect(ctx.offre).toBe('Logiciel de gestion pour dentistes');
		expect(ctx.tonDeMarque).toBe('chaleureux, direct');
		expect(ctx.clienteleCible).toBe('cabinets dentaires');
		// services : trim + déduplication, ordre préservé
		expect(ctx.services).toEqual(['prise de rendez-vous', 'facturation']);
	});

	it('tolère un bloc ```json``` autour du JSON', () => {
		const raw = '```json\n{"offre":"Boulangerie bio","services":["pain","viennoiserie"]}\n```';
		const ctx = parseSynthesis(raw);
		expect(ctx.offre).toBe('Boulangerie bio');
		expect(ctx.services).toEqual(['pain', 'viennoiserie']);
	});

	it('tolère du texte autour du JSON (extrait le premier objet)', () => {
		const raw = 'Voici ce que j’ai compris :\n{"offre":"Cabinet comptable"}\nJ’espère que c’est utile.';
		expect(parseSynthesis(raw).offre).toBe('Cabinet comptable');
	});

	it('champ manquant → vide (jamais halluciné)', () => {
		const ctx = parseSynthesis('{"offre":"X"}');
		expect(ctx.tonDeMarque).toBe('');
		expect(ctx.clienteleCible).toBe('');
		expect(ctx.services).toEqual([]);
	});

	it('neutralise les placeholders « non trouvé / inconnu » en vide', () => {
		const raw = JSON.stringify({
			offre: 'Inconnu',
			tonDeMarque: 'non trouvé',
			clienteleCible: 'N/A',
			services: ['—', 'Livraison']
		});
		const ctx = parseSynthesis(raw);
		expect(ctx.offre).toBe('');
		expect(ctx.tonDeMarque).toBe('');
		expect(ctx.clienteleCible).toBe('');
		expect(ctx.services).toEqual(['Livraison']);
	});

	it('valeurs non-string ignorées (types inattendus)', () => {
		const raw = JSON.stringify({ offre: 42, services: 'pas un tableau' });
		const ctx = parseSynthesis(raw);
		expect(ctx.offre).toBe('');
		expect(ctx.services).toEqual([]);
	});

	it('réponse illisible → contexte vide, sans lever', () => {
		expect(parseSynthesis('pas du tout du json')).toEqual(EMPTY_CONTEXT);
		expect(parseSynthesis('')).toEqual(EMPTY_CONTEXT);
	});
});

describe('isContextEmpty — honnêteté d’état', () => {
	it('vrai si tous les champs sont vides', () => {
		expect(isContextEmpty(EMPTY_CONTEXT)).toBe(true);
		expect(isContextEmpty({ offre: '  ', tonDeMarque: '', clienteleCible: '', services: [] })).toBe(
			true
		);
	});
	it('faux dès qu’un champ est renseigné', () => {
		expect(isContextEmpty({ ...EMPTY_CONTEXT, offre: 'X' })).toBe(false);
		expect(isContextEmpty({ ...EMPTY_CONTEXT, services: ['a'] })).toBe(false);
	});
});

describe('formatContextForProfile — texte USER.md lisible, champs vides omis', () => {
	it('assemble uniquement les champs renseignés', () => {
		const ctx: CompanyContext = {
			offre: 'Logiciel dentaire',
			tonDeMarque: 'direct',
			clienteleCible: 'cabinets',
			services: ['RDV', 'facturation']
		};
		const txt = formatContextForProfile(ctx);
		expect(txt).toContain('Logiciel dentaire');
		expect(txt).toContain('direct');
		expect(txt).toContain('cabinets');
		expect(txt).toContain('RDV');
		expect(txt).toContain('facturation');
	});

	it('omet les sections vides (pas de ligne fantôme)', () => {
		const txt = formatContextForProfile({ ...EMPTY_CONTEXT, offre: 'Juste une offre' });
		expect(txt).toContain('Juste une offre');
		expect(txt.toLowerCase()).not.toContain('ton de marque');
		expect(txt.toLowerCase()).not.toContain('services');
	});

	it('contexte vide → chaîne vide (rien à persister)', () => {
		expect(formatContextForProfile(EMPTY_CONTEXT)).toBe('');
	});
});

describe('buildSynthesisUserContent — borne la taille du markdown', () => {
	it('inclut le markdown', () => {
		expect(buildSynthesisUserContent('# Accueil\nNotre offre...')).toContain('Notre offre');
	});
	it('tronque un markdown gigantesque', () => {
		const huge = 'x'.repeat(100_000);
		expect(buildSynthesisUserContent(huge).length).toBeLessThan(huge.length);
	});
});
