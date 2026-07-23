import { describe, expect, it } from 'vitest';
import {
	answerToFact,
	buildExecutiveFacts,
	buildInterviewQuestions,
	buildMapMarkdown,
	enrichFactsWithUtility,
	mergeFacts,
	normalizeFacts
} from './logic';

describe('onboarding AgentOS', () => {
	it('normalise les faits et refuse les entrées vides', () => {
		const facts = normalizeFacts(
			[
				{ section: 'Clients et ICP', label: 'ICP', value: 'Restaurants multi-sites' },
				{ label: '', value: 'à ignorer' }
			],
			'web'
		);
		expect(facts).toHaveLength(1);
		expect(facts[0].status).toBe('a_confirmer');
		expect(facts[0].sourceType).toBe('web');
	});

	it('préserve une correction humaine lors d’un nouveau crawl', () => {
		const existing = normalizeFacts(
			[
				{
					id: 'site-icp',
					section: 'Clients et ICP',
					label: 'ICP',
					value: 'Restaurants',
					status: 'corrige'
				}
			],
			'site'
		);
		const incoming = normalizeFacts(
			[
				{
					id: 'site-icp-2',
					section: 'Clients et ICP',
					label: 'ICP',
					value: 'Tous commerces'
				}
			],
			'site'
		);
		expect(mergeFacts(existing, incoming)).toHaveLength(1);
		expect(mergeFacts(existing, incoming)[0].value).toBe('Restaurants');
	});

	it('transforme une réponse en fait confirmé', () => {
		const question = buildInterviewQuestions([])[0];
		const fact = answerToFact(question, { questionId: question.id, value: 'Abonnement mensuel' });
		expect(fact?.status).toBe('confirme');
		expect(fact?.sourceType).toBe('dirigeant');
	});

	it('ne redemande pas le nom déjà trouvé sur le site', () => {
		const facts = normalizeFacts(
			[
				{
					section: 'Identité et modèle économique',
					label: "Nom de l'entreprise",
					value: 'Zelty'
				}
			],
			'site'
		);
		expect(
			buildInterviewQuestions(facts).some((question) => question.id === 'nom-entreprise')
		).toBe(false);
	});

	it('génère une carte avec provenance', () => {
		const facts = normalizeFacts(
			[
				{
					section: 'Offres et positionnement',
					label: 'Offre',
					value: 'Logiciel métier',
					sourceUrl: 'https://example.com/offre'
				}
			],
			'site'
		);
		const markdown = buildMapMarkdown({
			companyName: 'Exemple',
			siteUrl: 'https://example.com',
			facts
		});
		expect(markdown).toContain('Déclaré sur le site de l’entreprise');
		expect(markdown).toContain('https://example.com/offre');
	});

	it('relie les faits aux objectifs sans vocabulaire sectoriel imposé', () => {
		const facts = normalizeFacts(
			[
				{
					section: 'Processus et tâches',
					label: 'Validation récurrente',
					value: 'La direction valide manuellement chaque dossier.'
				}
			],
			'site'
		);
		const enriched = enrichFactsWithUtility(facts, [
			{ id: 'efficacite', outcomeId: 'efficacite', label: 'Gagner du temps' }
		]);
		expect(enriched[0].utility?.purpose).toContain('répétitives');
		expect(enriched[0].utility?.workflowHint).toContain('Détecter');
	});

	it('limite la synthèse exécutive à quinze conclusions', () => {
		const facts = normalizeFacts(
			Array.from({ length: 30 }, (_, index) => ({
				section: index % 2 ? 'Offres et positionnement' : 'Clients et ICP',
				label: `Information ${index}`,
				value: `Élément distinct numéro ${index} avec une preuve ${index * 17}.`
			})),
			'site'
		);
		expect(buildExecutiveFacts(facts, [], 15).length).toBeLessThanOrEqual(15);
	});

	it('limite l’entretien à douze questions et tient compte des objectifs', () => {
		const questions = buildInterviewQuestions([], [
			{ id: 'qualite', outcomeId: 'qualite', label: 'Améliorer la qualité' }
		]);
		expect(questions).toHaveLength(12);
		expect(questions.find((question) => question.id === 'priorite')?.helper).toContain(
			'Améliorer la qualité'
		);
	});

	it('sépare la mémoire opérationnelle de l’annexe des preuves', () => {
		const facts = normalizeFacts(
			Array.from({ length: 20 }, (_, index) => ({
				section: 'Réputation et signaux',
				label: `Signal ${index}`,
				value: `Signal public distinct ${index} avec référence ${index * 31}.`
			})),
			'web'
		);
		const markdown = buildMapMarkdown({
			companyName: 'Entreprise générale',
			siteUrl: 'https://example.com',
			goals: [{ id: 'risques', outcomeId: 'risques', label: 'Réduire les risques' }],
			facts: enrichFactsWithUtility(facts, [
				{ id: 'risques', outcomeId: 'risques', label: 'Réduire les risques' }
			])
		});
		expect(markdown).toContain('Résultats prioritaires à 90 jours');
		expect(markdown).toContain('Annexe — preuves conservées en profondeur');
	});
});
