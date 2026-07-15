import { describe, it, expect } from 'vitest';
import {
	parseSynthesis,
	isContextEmpty,
	formatContextForProfile,
	formatContextForKnowledge,
	buildSynthesisUserContent,
	buildUserProfile,
	USER_PROFILE_MAX_CHARS,
	EMPTY_CONTEXT,
	type CompanyContext
} from './companySynthesis';

describe('parseSynthesis — jamais inventer, normaliser honnêtement', () => {
	it('parse un JSON complet (10 blocs) en CompanyContext', () => {
		const raw = JSON.stringify({
			nomEntreprise: 'DentaSoft',
			secteur: 'Logiciel médical',
			coordonnees: '01 23 45 67 89 · contact@dentasoft.fr · Paris',
			resume: 'DentaSoft édite un logiciel de gestion tout-en-un pour les cabinets dentaires.',
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
		expect(ctx.resume).toContain('tout-en-un pour les cabinets dentaires');
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

describe('formatContextForProfile — USER.md = ESSENCE seule (le nécessaire injecté partout)', () => {
	const rich: CompanyContext = {
		...EMPTY_CONTEXT,
		nomEntreprise: 'DentaSoft',
		secteur: 'Logiciel médical',
		coordonnees: 'Paris',
		resume: 'DentaSoft édite un logiciel pour cabinets dentaires.',
		offre: 'Logiciel dentaire',
		services: ['RDV', 'facturation'],
		tonDeMarque: 'direct',
		vocabulaire: ['cabinet connecté'],
		clienteleCible: 'cabinets',
		problemesResolus: 'trop d’outils',
		preuveSociale: ['500 cabinets']
	};

	it('garde l’essence : nom, secteur, résumé (activité), clientèle, ton, coordonnées', () => {
		const txt = formatContextForProfile(rich);
		expect(txt).toContain('DentaSoft');
		expect(txt).toContain('Logiciel médical');
		expect(txt).toContain('logiciel pour cabinets dentaires'); // le résumé sert d’activité
		expect(txt).toContain('cabinets');
		expect(txt).toContain('direct');
		expect(txt).toContain('Paris');
	});

	it('EXCLUT le verbeux (services, problèmes, preuves, vocabulaire) → réservé au coffre', () => {
		const txt = formatContextForProfile(rich);
		expect(txt).not.toContain('RDV');
		expect(txt).not.toContain('trop d’outils');
		expect(txt).not.toContain('500 cabinets');
		expect(txt).not.toContain('cabinet connecté');
	});

	it('repli sur l’offre si aucun résumé', () => {
		const txt = formatContextForProfile({ ...EMPTY_CONTEXT, offre: 'Juste une offre' });
		expect(txt).toContain('Juste une offre');
		expect(txt.toLowerCase()).not.toContain('ton de marque');
		expect(txt.toLowerCase()).not.toContain('preuves');
	});

	it('contexte vide → chaîne vide (rien à persister)', () => {
		expect(formatContextForProfile(EMPTY_CONTEXT)).toBe('');
	});
});

describe('formatContextForKnowledge — coffre = fiche COMPLÈTE (tout, sans borne)', () => {
	it('inclut résumé + tous les blocs (services, problèmes, preuves, vocabulaire)', () => {
		const ctx: CompanyContext = {
			...EMPTY_CONTEXT,
			nomEntreprise: 'DentaSoft',
			resume: 'Logiciel dentaire tout-en-un.',
			offre: 'Logiciel dentaire',
			services: ['RDV', 'facturation'],
			problemesResolus: 'trop d’outils',
			preuveSociale: ['500 cabinets équipés'],
			vocabulaire: ['cabinet connecté']
		};
		const txt = formatContextForKnowledge(ctx);
		expect(txt).toContain('Logiciel dentaire tout-en-un'); // résumé
		expect(txt).toContain('RDV'); // services conservés
		expect(txt).toContain('trop d’outils'); // problèmes conservés
		expect(txt).toContain('500 cabinets équipés'); // preuves verbatim
		expect(txt).toContain('cabinet connecté'); // vocabulaire complet
	});

	it('contexte vide → chaîne vide', () => {
		expect(formatContextForKnowledge(EMPTY_CONTEXT)).toBe('');
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

// Le backend REFUSE (400) un USER.md au-delà de 1375 caractères, et l'onboarding avalait cette
// erreur en silence : le contexte de l'entreprise était perdu sans un mot, au moment le plus
// critique du parcours. La seule vraie garantie est de ne jamais dépasser.
describe('buildUserProfile — ne dépasse JAMAIS la limite de USER.md', () => {
	const ligne = (n: number) => `- Ligne ${n} : ${'texte '.repeat(8)}`;
	const long = (n: number) =>
		Array.from({ length: n }, (_, i) => ligne(i)).join('\n');

	it('laisse passer un contexte et un profil courts', () => {
		const out = buildUserProfile('- Secteur : restauration', '- Prénom : Michael');
		expect(out).toContain('- Secteur : restauration');
		expect(out).toContain('- Prénom : Michael');
	});

	it('reste sous la limite quand le profil dirigeant est énorme', () => {
		const out = buildUserProfile(long(40), long(60));
		expect(out.length).toBeLessThanOrEqual(USER_PROFILE_MAX_CHARS);
	});

	// LE cas qui cassait : un profil qui remplit déjà le budget + le plancher de 200 du contexte.
	it('reste sous la limite même quand le profil seul dépasse le budget', () => {
		const profilSeul = long(200);
		expect(profilSeul.length).toBeGreaterThan(USER_PROFILE_MAX_CHARS);
		const out = buildUserProfile(long(30), profilSeul);
		expect(out.length).toBeLessThanOrEqual(USER_PROFILE_MAX_CHARS);
	});

	it('garde le profil dirigeant en priorité sur la fiche entreprise', () => {
		const out = buildUserProfile('- Secteur : restauration', '- Prénom : Michael');
		expect(out.indexOf('Michael')).toBeGreaterThan(-1);
	});

	it('accepte un contexte vide', () => {
		expect(buildUserProfile('', '- Prénom : Michael')).toBe('- Prénom : Michael');
	});

	it('accepte un profil vide', () => {
		expect(buildUserProfile('- Secteur : restauration', '')).toBe('- Secteur : restauration');
	});

	it('rend une chaîne vide quand tout est vide', () => {
		expect(buildUserProfile('', '')).toBe('');
	});
});
