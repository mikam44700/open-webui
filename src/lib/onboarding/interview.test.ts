import { describe, it, expect } from 'vitest';
import {
	buildQuestions,
	buildPages,
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

describe('buildPages — regroupement thématique', () => {
	it('avec site : 2 pages, prénom en tête, quotidien couvert', () => {
		const pages = buildPages(true);
		expect(pages.length).toBe(2);
		expect(pages[0].questions[0].key).toBe('prenom');
		const keys = pages.flatMap((p) => p.questions.map((q) => q.key));
		expect(keys).toContain('faconTravailler');
	});

	it('sans site : couvre l’entreprise (dont vocabulaire + problèmes résolus), ≤4 questions/page', () => {
		const pages = buildPages(false);
		const keys = pages.flatMap((p) => p.questions.map((q) => q.key));
		expect(keys).toContain('nomEntreprise');
		expect(keys).toContain('offre');
		expect(keys).toContain('problemesResolus');
		expect(keys).toContain('vocabulaire');
		for (const p of pages) expect(p.questions.length).toBeLessThanOrEqual(4);
	});

	it('le prénom (seul requis) est sur la 1re page', () => {
		const first = buildPages(false)[0];
		expect(first.questions.some((q) => q.key === 'prenom' && !q.optional)).toBe(true);
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
	it('mappe l’identité, génère le résumé et route les problèmes résolus', () => {
		const ctx = answersToContext({
			nomEntreprise: 'Plomberie Martin',
			secteur: 'Plomberie et chauffage pour particuliers',
			offre: 'dépannage et installation, en forfait ou à l’unité',
			clienteleCible: 'propriétaires de maisons',
			problemesResolus: 'pannes urgentes et vieilles chaudières',
			prenom: 'Marc' // profil, ignoré ici
		});
		expect(ctx.nomEntreprise).toBe('Plomberie Martin');
		expect(ctx.secteur).toBe('Plomberie et chauffage pour particuliers');
		expect(ctx.clienteleCible).toBe('propriétaires de maisons');
		// l'offre a désormais SA question dédiée (distincte du secteur)
		expect(ctx.offre).toBe('dépannage et installation, en forfait ou à l’unité');
		// la question « quel problème réglez-vous » alimente SON bloc (parité avec le crawl)
		expect(ctx.problemesResolus).toBe('pannes urgentes et vieilles chaudières');
		// le résumé (ADN) est généré depuis nom + activité → USER.md n'est jamais sans phrase d'accroche
		expect(ctx.resume).toContain('Plomberie Martin');
		expect(ctx.resume).toContain('Plomberie et chauffage');
		// champs non captés restent vides
		expect(ctx.services).toEqual([]);
	});

	it('résumé vide si ni nom ni activité renseignés', () => {
		expect(answersToContext({}).resume).toBe('');
		expect(answersToContext({ clienteleCible: 'des artisans' }).resume).toBe('');
	});

	it('PARITÉ CRAWL : avec toutes les réponses, AUCUN des 11 blocs de la fiche n’est vide', () => {
		// Réponses complètes de l'interview « sans site » (une par bloc que le crawl produirait).
		const ctx = answersToContext({
			nomEntreprise: 'Zelty',
			secteur: 'logiciel de caisse et de gestion pour les restaurants',
			offre: 'solution en abonnement mensuel sans engagement',
			services: 'Caisse (POS)\nLivraison\nClick & collect',
			clienteleCible: 'restaurateurs et gérants d’établissements',
			problemesResolus: 'simplifier la gestion quotidienne des restaurants',
			tonDeMarque: 'Professionnel',
			vocabulaire: 'POS\nKDS\nDark kitchen',
			preuveSociale: 'plus de 4 000 restaurants\n10 ans d’expérience',
			coordonnees: 'support@zelty.fr — Paris'
		});
		// On balaie TOUTES les clés du CompanyContext produit : aucune ne doit rester vide.
		const vides = Object.entries(ctx).filter(([, v]) =>
			Array.isArray(v) ? v.length === 0 : String(v).trim() === ''
		);
		expect(vides.map(([k]) => k)).toEqual([]); // ← liste les blocs oubliés s'il y en avait
	});

	it('reverse services, ton, vocabulaire, preuves et coordonnées (listes par ligne)', () => {
		const ctx = answersToContext({
			nomEntreprise: 'Plomberie Martin',
			services: 'Dépannage\nInstallation de chaudières',
			tonDeMarque: 'Chaleureux',
			vocabulaire: 'PAC\nballon thermodynamique',
			preuveSociale: '20 ans d’expérience\n4,8/5 sur Google',
			coordonnees: '06 12 34 56 78, contact@martin.fr'
		});
		expect(ctx.services).toEqual(['Dépannage', 'Installation de chaudières']);
		expect(ctx.tonDeMarque).toBe('Chaleureux');
		expect(ctx.vocabulaire).toEqual(['PAC', 'ballon thermodynamique']);
		// la virgule décimale (4,8) est préservée : on découpe par ligne, jamais par virgule
		expect(ctx.preuveSociale).toEqual(['20 ans d’expérience', '4,8/5 sur Google']);
		expect(ctx.coordonnees).toBe('06 12 34 56 78, contact@martin.fr');
	});
});
