import { describe, expect, it } from 'vitest';
import {
	answerToFact,
	buildExecutiveFacts,
	buildExternalBusinessSignals,
	buildExternalSearchQueries,
	buildInterviewQuestions,
	buildMapMarkdown,
	buildPriorityInsights,
	diversifyExternalFactsByDomain,
	enrichFactsWithUtility,
	filterAndDiversifyExternalItems,
	mergeFacts,
	normalizeFacts,
	prepareActionDraft,
	sourceDomain
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

	it('limite l’entretien à cinq questions et tient compte des objectifs', () => {
		const questions = buildInterviewQuestions(
			[],
			[{ id: 'qualite', outcomeId: 'qualite', label: 'Améliorer la qualité' }]
		);
		expect(questions).toHaveLength(5);
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

	it('construit une recherche extérieure qui ne dépend pas seulement du nom du client', () => {
		const queries = buildExternalSearchQueries({
			companyName: 'Entreprise Exemple',
			siteUrl: 'https://entreprise-exemple.fr',
			sectorHint: 'logiciel de gestion pour cabinets médicaux',
			offerHint: 'automatisation des rendez-vous',
			icpHint: 'directeurs de cliniques privées',
			problemHint: 'temps perdu dans les tâches administratives',
			goals: [{ id: 'revenus', outcomeId: 'revenus', label: 'Développer les revenus' }]
		});
		expect(queries).toHaveLength(4);
		expect(queries.filter((query) => query.includes('Entreprise Exemple'))).toHaveLength(3);
		expect(queries.filter((query) => !query.includes('Entreprise Exemple'))).toHaveLength(1);
		expect(queries.join(' ')).toContain('tendances risques marché France');
	});

	it('exclut le domaine du client, déduplique les URL et diversifie les domaines', () => {
		const items = [
			{
				title: 'Site officiel',
				link: 'https://www.client.fr/actualites',
				snippet: 'À exclure'
			},
			{
				title: 'Sous-domaine officiel',
				link: 'https://blog.client.fr/article',
				snippet: 'À exclure aussi'
			},
			...Array.from({ length: 4 }, (_, index) => ({
				title: `Source A ${index}`,
				link: `https://source-a.test/article-${index}?utm_source=test`,
				snippet: `Analyse ${index}`
			})),
			{
				title: 'Doublon',
				link: 'https://source-a.test/article-0',
				snippet: 'Même URL canonique'
			},
			{
				title: 'Source B',
				link: 'https://source-b.test/etude',
				snippet: 'Étude indépendante'
			},
			{
				title: 'Source C',
				link: 'https://source-c.test/tendance',
				snippet: 'Tendance marché'
			}
		];
		const results = filterAndDiversifyExternalItems(items, 'https://client.fr', 2, 10);
		expect(results.map((item) => item.link).join(' ')).not.toContain('client.fr');
		expect(results.filter((item) => item.link.includes('source-a.test'))).toHaveLength(2);
		expect(results.slice(0, 3).map((item) => new URL(item.link).hostname)).toEqual([
			'source-a.test',
			'source-b.test',
			'source-c.test'
		]);
	});

	it('empêche un seul domaine de monopoliser les faits Web', () => {
		const facts = Array.from({ length: 8 }, (_, index) => ({
			id: `web-${index}`,
			section: 'Concurrence et marché',
			label: `Signal ${index}`,
			value: `Valeur ${index}`,
			sourceType: 'web' as const,
			sourceUrl:
				index < 6
					? `https://dominant.example/article-${index}`
					: `https://source-${index}.example/article`,
			observedAt: '2026-07-23',
			status: 'a_confirmer' as const,
			confidence: 0.8
		}));

		const diversified = diversifyExternalFactsByDomain(facts, 2, 8);
		expect(diversified.filter((fact) => fact.sourceUrl?.includes('dominant.example'))).toHaveLength(
			2
		);
		expect(new Set(diversified.map((fact) => sourceDomain(fact.sourceUrl ?? ''))).size).toBe(3);
	});

	it('classe au maximum cinq signaux business prouvés et liés aux priorités choisies', () => {
		const goals = [
			{ id: 'revenus', outcomeId: 'revenus' as const, label: 'Développer les revenus' },
			{ id: 'clients', outcomeId: 'clients' as const, label: 'Mieux servir les clients' }
		];
		const facts = normalizeFacts(
			[
				{
					section: 'Réputation et signaux',
					label: 'Attente de réponse rapide',
					value: 'Des acheteurs interrogés valorisent une réponse commerciale dans la journée.',
					sourceUrl: 'https://source-a.test/reponse',
					confidence: 0.9,
					businessSignal: {
						kind: 'besoin_client',
						goalId: 'clients',
						whyItMatters: 'Cette attente peut modifier la qualité de la réponse client.',
						nextAction: 'Comparer cette attente au délai de réponse actuel.'
					}
				},
				{
					section: 'Réputation et signaux',
					label: 'Préférence pour le libre-service',
					value: 'Une étude montre une préférence croissante pour une documentation autonome.',
					sourceUrl: 'https://source-a.test/libre-service',
					confidence: 0.85,
					businessSignal: {
						kind: 'besoin_client',
						goalId: 'clients',
						whyItMatters: 'Le libre-service peut améliorer l’expérience avant contact.',
						nextAction: 'Identifier les trois questions client les plus fréquentes.'
					}
				},
				{
					section: 'Réputation et signaux',
					label: 'Troisième fait du même domaine',
					value: 'Un baromètre évoque une demande nouvelle pour des contrats plus souples.',
					sourceUrl: 'https://source-a.test/contrats',
					confidence: 0.8,
					businessSignal: {
						kind: 'besoin_client',
						goalId: 'clients',
						whyItMatters: 'La souplesse peut peser dans le choix du fournisseur.',
						nextAction: 'Vérifier les objections contractuelles dans les ventes perdues.'
					}
				},
				{
					section: 'Concurrence et marché',
					label: 'Nouveau segment régional',
					value: 'Un rapport sectoriel constate une hausse des achats dans les villes secondaires.',
					sourceUrl: 'https://source-b.test/regions',
					confidence: 0.8,
					businessSignal: {
						kind: 'opportunite',
						goalId: 'revenus',
						whyItMatters: 'Ce segment peut soutenir la priorité de développement.',
						nextAction: 'Comparer ces zones avec les clients qui convertissent déjà.'
					}
				},
				{
					section: 'Concurrence et marché',
					label: 'Concurrent avec une offre allégée',
					value: 'Un nouvel entrant lance une formule simplifiée destinée aux petites équipes.',
					sourceUrl: 'https://source-c.test/concurrent',
					confidence: 0.8,
					businessSignal: {
						kind: 'mouvement_concurrent',
						goalId: 'revenus',
						whyItMatters: 'Cette offre peut changer les critères de comparaison.',
						nextAction: 'Préparer une fiche de différenciation à faire valider.'
					}
				},
				{
					section: 'Concurrence et marché',
					label: 'Canal partenaire émergent',
					value: 'Des distributeurs spécialisés ouvrent un programme de recommandation commun.',
					sourceUrl: 'https://source-d.test/partenaires',
					confidence: 0.8,
					businessSignal: {
						kind: 'opportunite',
						goalId: 'revenus',
						whyItMatters: 'Ce canal pourrait élargir l’accès aux prospects.',
						nextAction: 'Évaluer le recouvrement avec le profil client prioritaire.'
					}
				},
				{
					section: 'Concurrence et marché',
					label: 'Réglementation annoncée',
					value: 'Une autorité prépare une nouvelle exigence de traçabilité numérique.',
					sourceUrl: 'https://source-e.test/reglementation',
					confidence: 0.8,
					businessSignal: {
						kind: 'risque',
						goalId: 'clients',
						whyItMatters: 'Cette exigence peut créer de nouvelles questions clients.',
						nextAction: 'Faire qualifier la portée par le responsable concerné.'
					}
				},
				{
					section: 'Concurrence et marché',
					label: 'Priorité absente',
					value: 'Ce fait pointe vers une priorité qui n’a pas été choisie.',
					sourceUrl: 'https://source-invalide.test/fait',
					businessSignal: {
						kind: 'risque',
						goalId: 'risques',
						whyItMatters: 'Risque extérieur.',
						nextAction: 'Analyser le risque.'
					}
				}
			],
			'web'
		);
		const signals = buildExternalBusinessSignals(facts, goals, 5);
		expect(signals).toHaveLength(5);
		expect(signals.filter((fact) => fact.sourceUrl?.includes('source-a.test'))).toHaveLength(2);
		expect(
			signals.every((fact) => goals.some((goal) => goal.id === fact.businessSignal?.goalId))
		).toBe(true);
	});

	it('fusionne les doublons prioritaires, conserve les preuves et signale les contradictions', () => {
		const goals = [
			{ id: 'objectif-revenus', outcomeId: 'revenus' as const, label: 'Développer les revenus' }
		];
		const facts = normalizeFacts(
			[
				{
					id: 'source-a',
					section: 'Concurrence et marché',
					label: 'Tarif du concurrent Alpha',
					value: 'Le tarif annoncé est de 49 € par mois.',
					sourceUrl: 'https://source-a.test/prix',
					confidence: 0.9,
					businessSignal: {
						kind: 'mouvement_concurrent',
						goalId: 'objectif-revenus',
						whyItMatters: 'Ce tarif change la comparaison commerciale.',
						nextAction: 'Préparer un argumentaire de différenciation.'
					}
				},
				{
					id: 'source-b',
					section: 'Concurrence et marché',
					label: 'Prix du concurrent Alpha',
					value: 'Le tarif observé est de 79 € par mois.',
					sourceUrl: 'https://source-b.test/alpha',
					confidence: 0.8,
					businessSignal: {
						kind: 'mouvement_concurrent',
						goalId: 'objectif-revenus',
						whyItMatters: 'Ce tarif change la comparaison commerciale.',
						nextAction: 'Préparer un argumentaire de différenciation.'
					}
				}
			],
			'web'
		);
		const insights = buildPriorityInsights(facts, goals);
		expect(insights).toHaveLength(1);
		expect(insights[0].evidenceFactIds).toHaveLength(2);
		expect(insights[0].contradictionFactIds).toEqual(['source-b']);
		expect(insights[0].goalId).toBe('objectif-revenus');
	});

	it('plafonne la vue à huit cartes et prépare un brouillon idempotent sans exécution', () => {
		const goals = [
			{ id: 'objectif-clients', outcomeId: 'clients' as const, label: 'Mieux servir les clients' }
		];
		const subjects = [
			'Délai de réponse commerciale',
			'Qualité du support technique',
			'Clarté des contrats annuels',
			'Disponibilité de la documentation',
			'Simplicité de la facturation',
			'Personnalisation de l’accompagnement',
			'Fréquence des comptes rendus',
			'Continuité du service',
			'Formation des nouveaux utilisateurs',
			'Suivi des demandes urgentes',
			'Accessibilité des équipes',
			'Mesure de la satisfaction'
		];
		const facts = normalizeFacts(
			subjects.map((label, index) => ({
				id: `fact-${index}`,
				section: 'Clients et ICP',
				label,
				value: `Attente spécifique numéro ${index}`,
				confidence: 0.8
			})),
			'site'
		);
		const insights = buildPriorityInsights(facts, goals);
		expect(insights.length).toBeLessThanOrEqual(5);
		const first = prepareActionDraft(insights[0]);
		expect(prepareActionDraft(insights[0], first)).toBe(first);
		expect(first.status).toBe('À valider');
		expect(first.evidenceFactIds.length).toBeGreaterThan(0);
	});
});
