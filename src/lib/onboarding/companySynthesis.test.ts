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
	it('parse un JSON complet (10 blocs) en CompanyContext', () => {
		const raw = JSON.stringify({
			nomEntreprise: 'DentaSoft',
			secteur: 'Logiciel médical',
			coordonnees: '01 23 45 67 89 · contact@dentasoft.fr · Paris',
			offre: 'Logiciel de gestion pour dentistes',
			services: ['prise de rendez-vous', 'facturation', 'facturation'],
			tonDeMarque: 'chaleureux, direct',
			vocabulaire: ['cabinet connecté', 'cabinet connecté'],
			clienteleCible: 'cabinets dentaires',
			problemesResolus: 'trop de logiciels différents à gérer',
			preuveSociale: ['500 cabinets équipés', '4,8/5 sur Google']
		});
		const ctx = parseSynthesis(raw);
		expect(ctx.nomEntreprise).toBe('DentaSoft');
		expect(ctx.secteur).toBe('Logiciel médical');
		expect(ctx.coordonnees).toContain('01 23 45 67 89');
		expect(ctx.offre).toBe('Logiciel de gestion pour dentistes');
		expect(ctx.tonDeMarque).toBe('chaleureux, direct');
		expect(ctx.clienteleCible).toBe('cabinets dentaires');
		expect(ctx.problemesResolus).toBe('trop de logiciels différents à gérer');
		// listes : trim + déduplication, ordre préservé
		expect(ctx.services).toEqual(['prise de rendez-vous', 'facturation']);
		expect(ctx.vocabulaire).toEqual(['cabinet connecté']);
		expect(ctx.preuveSociale).toEqual(['500 cabinets équipés', '4,8/5 sur Google']);
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
		expect(ctx.nomEntreprise).toBe('');
		expect(ctx.problemesResolus).toBe('');
		expect(ctx.services).toEqual([]);
		expect(ctx.preuveSociale).toEqual([]);
		expect(ctx.vocabulaire).toEqual([]);
	});

	it('neutralise les placeholders « non trouvé / inconnu » en vide', () => {
		const raw = JSON.stringify({
			offre: 'Inconnu',
			tonDeMarque: 'non trouvé',
			clienteleCible: 'N/A',
			problemesResolus: 'non renseigné',
			coordonnees: 'non disponible',
			services: ['—', 'Livraison'],
			preuveSociale: ['aucune']
		});
		const ctx = parseSynthesis(raw);
		expect(ctx.offre).toBe('');
		expect(ctx.tonDeMarque).toBe('');
		expect(ctx.clienteleCible).toBe('');
		expect(ctx.problemesResolus).toBe('');
		expect(ctx.coordonnees).toBe('');
		expect(ctx.services).toEqual(['Livraison']);
		expect(ctx.preuveSociale).toEqual([]);
	});

	it('valeurs non-string ignorées (types inattendus)', () => {
		const raw = JSON.stringify({ offre: 42, services: 'pas un tableau', preuveSociale: 7 });
		const ctx = parseSynthesis(raw);
		expect(ctx.offre).toBe('');
		expect(ctx.services).toEqual([]);
		expect(ctx.preuveSociale).toEqual([]);
	});

	it('réponse illisible → contexte vide, sans lever', () => {
		expect(parseSynthesis('pas du tout du json')).toEqual(EMPTY_CONTEXT);
		expect(parseSynthesis('')).toEqual(EMPTY_CONTEXT);
	});
});

describe('isContextEmpty — honnêteté d’état', () => {
	it('vrai si tous les champs sont vides', () => {
		expect(isContextEmpty(EMPTY_CONTEXT)).toBe(true);
		expect(isContextEmpty({ ...EMPTY_CONTEXT, offre: '  ' })).toBe(true);
	});
	it('faux dès qu’un champ (ancien OU nouveau) est renseigné', () => {
		expect(isContextEmpty({ ...EMPTY_CONTEXT, offre: 'X' })).toBe(false);
		expect(isContextEmpty({ ...EMPTY_CONTEXT, services: ['a'] })).toBe(false);
		expect(isContextEmpty({ ...EMPTY_CONTEXT, nomEntreprise: 'Acme' })).toBe(false);
		expect(isContextEmpty({ ...EMPTY_CONTEXT, preuveSociale: ['1000 clients'] })).toBe(false);
		expect(isContextEmpty({ ...EMPTY_CONTEXT, coordonnees: 'Paris' })).toBe(false);
	});
});

describe('formatContextForProfile — texte USER.md lisible, champs vides omis', () => {
	it('assemble tous les champs renseignés', () => {
		const ctx: CompanyContext = {
			...EMPTY_CONTEXT,
			nomEntreprise: 'DentaSoft',
			secteur: 'Logiciel médical',
			coordonnees: 'Paris',
			offre: 'Logiciel dentaire',
			services: ['RDV', 'facturation'],
			tonDeMarque: 'direct',
			vocabulaire: ['cabinet connecté'],
			clienteleCible: 'cabinets',
			problemesResolus: 'trop d’outils',
			preuveSociale: ['500 cabinets']
		};
		const txt = formatContextForProfile(ctx);
		expect(txt).toContain('DentaSoft');
		expect(txt).toContain('Logiciel médical');
		expect(txt).toContain('Logiciel dentaire');
		expect(txt).toContain('cabinets');
		expect(txt).toContain('RDV');
		expect(txt).toContain('trop d’outils');
		expect(txt).toContain('500 cabinets');
		expect(txt).toContain('cabinet connecté');
		expect(txt).toContain('Paris');
	});

	it('omet les sections vides (pas de ligne fantôme)', () => {
		const txt = formatContextForProfile({ ...EMPTY_CONTEXT, offre: 'Juste une offre' });
		expect(txt).toContain('Juste une offre');
		expect(txt.toLowerCase()).not.toContain('ton de marque');
		expect(txt.toLowerCase()).not.toContain('preuves');
		expect(txt.toLowerCase()).not.toContain('coordonnées');
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
