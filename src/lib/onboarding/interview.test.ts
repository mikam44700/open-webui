import { describe, it, expect } from 'vitest';
import {
	buildQuestions,
	formatInterviewForProfile,
	answersToContext,
	isInterviewEmpty,
	COMPLEMENT_QUESTIONS,
	NO_SITE_QUESTIONS,
	type Answers
} from './interview';

describe('buildQuestions — séquence adaptée au contexte', () => {
	it('avec site : uniquement les compléments (courts)', () => {
		const qs = buildQuestions(true);
		expect(qs).toEqual(COMPLEMENT_QUESTIONS);
		expect(qs.length).toBeLessThanOrEqual(8);
		expect(qs[0].key).toBe('prenom'); // engagement d'abord
	});

	it('sans site : prénom + bases entreprise + compléments', () => {
		const qs = buildQuestions(false);
		expect(qs[0].key).toBe('prenom');
		// les bases entreprise sont insérées après le prénom
		const keys = qs.map((q) => q.key);
		for (const q of NO_SITE_QUESTIONS) expect(keys).toContain(q.key);
		expect(keys.indexOf('nomEntreprise')).toBeGreaterThan(0);
		expect(keys.indexOf('nomEntreprise')).toBeLessThan(keys.indexOf('tailleEquipe'));
	});

	it('toutes les questions sauf le prénom sont skippables', () => {
		for (const q of COMPLEMENT_QUESTIONS) {
			if (q.key === 'prenom') expect(q.optional).toBeFalsy();
			else expect(q.optional).toBe(true);
		}
	});
});

describe('isInterviewEmpty', () => {
	it('vrai si aucune réponse', () => {
		expect(isInterviewEmpty({})).toBe(true);
		expect(isInterviewEmpty({ prenom: '  ', outils: [] })).toBe(true);
	});
	it('faux dès qu’une réponse existe', () => {
		expect(isInterviewEmpty({ prenom: 'Sophie' })).toBe(false);
		expect(isInterviewEmpty({ outils: ['E-mail'] })).toBe(false);
	});
});

describe('formatInterviewForProfile — section USER.md, champs vides omis', () => {
	it('assemble les réponses de profil connues', () => {
		const a: Answers = {
			prenom: 'Sophie',
			role: 'Gérante',
			tailleEquipe: '2 à 5',
			outils: ['E-mail', 'CRM'],
			priorite: 'décrocher plus de clients',
			faconTravailler: 'Un mix des deux',
			tacheAgacante: 'relancer les impayés'
		};
		const txt = formatInterviewForProfile(a);
		expect(txt).toContain('## Mon profil');
		expect(txt).toContain('Sophie');
		expect(txt).toContain('Gérante');
		expect(txt).toContain('2 à 5');
		expect(txt).toContain('E-mail, CRM'); // liste jointe
		expect(txt).toContain('relancer les impayés');
	});

	it('exclut les clés de contexte entreprise (nom, secteur, ton, services…)', () => {
		const txt = formatInterviewForProfile({
			prenom: 'Léa',
			nomEntreprise: 'Acme',
			secteur: 'BTP',
			tonDeMarque: 'Direct',
			services: 'Toiture'
		});
		expect(txt).toContain('Léa');
		expect(txt).not.toContain('Acme');
		expect(txt).not.toContain('BTP');
		expect(txt).not.toContain('Direct');
		expect(txt).not.toContain('Toiture');
	});

	it('aucune réponse de profil → chaîne vide', () => {
		expect(formatInterviewForProfile({})).toBe('');
		expect(formatInterviewForProfile({ nomEntreprise: 'Acme' })).toBe('');
	});
});

describe('answersToContext — cas sans site : réponses → fiche entreprise', () => {
	it('reverse nom/secteur/clientèle/offre dans le contexte', () => {
		const ctx = answersToContext({
			nomEntreprise: 'Plomberie Martin',
			secteur: 'Plomberie et chauffage',
			clienteleCible: 'particuliers',
			offre: 'dépannage et installation',
			prenom: 'Marc' // profil, ignoré ici
		});
		expect(ctx.nomEntreprise).toBe('Plomberie Martin');
		expect(ctx.secteur).toBe('Plomberie et chauffage');
		expect(ctx.clienteleCible).toBe('particuliers');
		expect(ctx.offre).toBe('dépannage et installation');
		// les champs non captés par l'interview restent vides (pas de site à lire)
		expect(ctx.services).toEqual([]);
		expect(ctx.coordonnees).toBe('');
	});

	it('reverse aussi services, ton, preuves et coordonnées (listes découpées par ligne)', () => {
		const ctx = answersToContext({
			nomEntreprise: 'Plomberie Martin',
			services: 'Dépannage\nInstallation de chaudières',
			tonDeMarque: 'Chaleureux',
			preuveSociale: '20 ans d’expérience\n4,8/5 sur Google',
			coordonnees: '06 12 34 56 78, contact@martin.fr'
		});
		expect(ctx.services).toEqual(['Dépannage', 'Installation de chaudières']);
		expect(ctx.tonDeMarque).toBe('Chaleureux');
		// la virgule décimale (4,8) est préservée : on découpe par ligne, jamais par virgule
		expect(ctx.preuveSociale).toEqual(['20 ans d’expérience', '4,8/5 sur Google']);
		expect(ctx.coordonnees).toBe('06 12 34 56 78, contact@martin.fr');
	});
});
