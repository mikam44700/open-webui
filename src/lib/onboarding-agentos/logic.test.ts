import { describe, expect, it } from 'vitest';
import {
	answerToFact,
	buildInterviewQuestions,
	buildMapMarkdown,
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
		expect(markdown).toContain('Trouvé sur le site');
		expect(markdown).toContain('https://example.com/offre');
	});
});
