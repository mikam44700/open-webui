import type {
	BusinessGoal,
	BusinessOutcomeId,
	EvidenceFact,
	InterviewAnswer,
	InterviewQuestion,
	OperationalMap,
	WorkflowProposal
} from './types';

export const DRAFT_KEY = 'lunaria_agentos_onboarding_draft_v1';
export const DONE_KEY = 'lunaria_agentos_onboarding_v1_done';
export const SKIP_ONCE_KEY = 'lunaria_agentos_onboarding_skip_once';
export const COMPANY_MAP_NOTE_ID = 'lunaria-company-operational-map-v1';
export const COMPANY_MAP_NOTE_TITLE = "Carte opérationnelle de l'entreprise";
export const WORKFLOW_NOTE_ID = 'lunaria-selected-workflow-v1';
export const WORKFLOW_NOTE_TITLE = 'Premier workflow LunarIA';

export const SECTION_ORDER = [
	'Identité et modèle économique',
	'Offres et positionnement',
	'Clients et ICP',
	'Concurrence et marché',
	'Réputation et signaux',
	'Organisation et responsabilités',
	'Processus et tâches',
	'Outils et sources de vérité',
	'Pertes, risques et priorités',
	'Objectifs et indicateurs',
	'Règles et permissions'
];

export const GOAL_CATALOG: BusinessGoal[] = [
	{
		id: 'objectif-revenus',
		outcomeId: 'revenus',
		label: 'Développer les revenus',
		detail: 'Vendre davantage, mieux convertir ou protéger la marge.'
	},
	{
		id: 'objectif-clients',
		outcomeId: 'clients',
		label: 'Mieux servir et fidéliser les clients',
		detail: 'Améliorer l’expérience, la satisfaction ou la rétention.'
	},
	{
		id: 'objectif-efficacite',
		outcomeId: 'efficacite',
		label: 'Gagner du temps et réduire les coûts',
		detail: 'Simplifier les tâches, processus et coordinations répétitives.'
	},
	{
		id: 'objectif-qualite',
		outcomeId: 'qualite',
		label: 'Améliorer la qualité',
		detail: 'Rendre la production ou le service plus fiable et plus constant.'
	},
	{
		id: 'objectif-risques',
		outcomeId: 'risques',
		label: 'Réduire les risques et les erreurs',
		detail: 'Mieux contrôler les décisions sensibles, anomalies et obligations.'
	},
	{
		id: 'objectif-connaissance',
		outcomeId: 'connaissance',
		label: 'Mieux partager la connaissance',
		detail: 'Retrouver le savoir, fluidifier les décisions et moins dépendre des personnes.'
	}
];

export const EXECUTIVE_GROUPS = [
	{
		label: 'Entreprise et valeur',
		sections: ['Identité et modèle économique', 'Offres et positionnement']
	},
	{
		label: 'Clients et développement',
		sections: ['Clients et ICP', 'Concurrence et marché', 'Réputation et signaux']
	},
	{
		label: 'Organisation et opérations',
		sections: ['Organisation et responsabilités', 'Processus et tâches']
	},
	{ label: 'Outils et connaissance', sections: ['Outils et sources de vérité'] },
	{ label: 'Problèmes et priorités', sections: ['Pertes, risques et priorités'] },
	{
		label: 'Résultats et garde-fous',
		sections: ['Objectifs et indicateurs', 'Règles et permissions']
	}
];

const today = () => new Date().toISOString().slice(0, 10);

const compact = (value: string) => value.trim().replace(/\s+/g, ' ');

export const safeId = (value: string) =>
	value
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '')
		.slice(0, 80);

export const normalizeFacts = (
	input: Partial<EvidenceFact>[],
	fallbackSource: 'site' | 'web'
): EvidenceFact[] => {
	const seen = new Set<string>();
	const output: EvidenceFact[] = [];
	for (const raw of input) {
		const label = compact(String(raw.label ?? ''));
		const value = compact(String(raw.value ?? ''));
		const section = SECTION_ORDER.includes(String(raw.section))
			? String(raw.section)
			: fallbackSource === 'site'
				? 'Offres et positionnement'
				: 'Concurrence et marché';
		if (!label || !value) continue;
		const fingerprint = `${section}|${label.toLowerCase()}|${value.toLowerCase()}`;
		if (seen.has(fingerprint)) continue;
		seen.add(fingerprint);
		const status =
			raw.status === 'confirme' || raw.status === 'corrige' ? raw.status : 'a_confirmer';
		output.push({
			id: raw.id || `${fallbackSource}-${safeId(label)}-${output.length + 1}`,
			section,
			label,
			value,
			sourceType: raw.sourceType ?? fallbackSource,
			sourceUrl: String(raw.sourceUrl ?? '').trim() || undefined,
			sourceTitle: String(raw.sourceTitle ?? '').trim() || undefined,
			observedAt: String(raw.observedAt ?? '').slice(0, 10) || today(),
			status,
			confidence: Math.max(0, Math.min(1, Number(raw.confidence ?? 0.6)))
		});
	}
	return output;
};

export const mergeFacts = (existing: EvidenceFact[], incoming: EvidenceFact[]): EvidenceFact[] => {
	const result = [...existing];
	for (const fact of incoming) {
		const exact = result.findIndex((candidate) => candidate.id === fact.id);
		if (exact >= 0) {
			if (result[exact].status !== 'corrige') result[exact] = fact;
			continue;
		}
		const humanCorrection = result.find(
			(candidate) =>
				candidate.status === 'corrige' &&
				candidate.section === fact.section &&
				candidate.label.toLowerCase() === fact.label.toLowerCase()
		);
		if (!humanCorrection) result.push(fact);
	}
	return result;
};

const SECTION_UTILITY: Record<
	string,
	{
		outcomes: BusinessOutcomeId[];
		purpose: string;
		decision: string;
		workflow: string;
		metric: string;
	}
> = {
	'Identité et modèle économique': {
		outcomes: ['revenus', 'connaissance'],
		purpose: 'Aligner les recommandations sur la manière dont l’entreprise crée ses revenus.',
		decision: 'Choisir les activités et revenus à prioriser.',
		workflow: 'Qualifier une demande selon le modèle économique réel.',
		metric: 'Revenu ou marge par activité.'
	},
	'Offres et positionnement': {
		outcomes: ['revenus', 'clients'],
		purpose: 'Personnaliser les argumentaires, réponses et contenus autour de la valeur vendue.',
		decision: 'Choisir quelle offre proposer et comment la présenter.',
		workflow: 'Préparer une réponse commerciale ou un contenu adapté.',
		metric: 'Taux de conversion par offre.'
	},
	'Clients et ICP': {
		outcomes: ['revenus', 'clients'],
		purpose: 'Reconnaître les clients à privilégier et adapter les actions à leurs besoins.',
		decision: 'Prioriser un prospect, un segment ou une action de fidélisation.',
		workflow: 'Qualifier, personnaliser puis préparer la prochaine action client.',
		metric: 'Conversion, rétention ou valeur client.'
	},
	'Concurrence et marché': {
		outcomes: ['revenus', 'risques'],
		purpose: 'Éclairer le positionnement et détecter les changements qui appellent une réaction.',
		decision: 'Ajuster une offre, un discours ou une priorité de veille.',
		workflow: 'Détecter un changement, évaluer son impact et préparer une réponse.',
		metric: 'Opportunités ou menaces traitées.'
	},
	'Réputation et signaux': {
		outcomes: ['clients', 'risques'],
		purpose: 'Repérer les forces, irritants et signaux susceptibles d’affecter la confiance.',
		decision: 'Traiter un irritant client ou amplifier une preuve utile.',
		workflow: 'Surveiller un signal puis préparer une action de réponse.',
		metric: 'Satisfaction, avis ou incidents traités.'
	},
	'Organisation et responsabilités': {
		outcomes: ['efficacite', 'connaissance'],
		purpose: 'Acheminer chaque information et validation vers la bonne personne.',
		decision: 'Attribuer une responsabilité ou une validation.',
		workflow: 'Router une demande vers le responsable concerné.',
		metric: 'Délai de décision ou de traitement.'
	},
	'Processus et tâches': {
		outcomes: ['efficacite', 'qualite'],
		purpose: 'Identifier les étapes répétitives à assister, fiabiliser ou automatiser.',
		decision: 'Choisir le prochain processus à améliorer.',
		workflow: 'Détecter, préparer, faire valider, agir puis mesurer.',
		metric: 'Temps économisé, coût ou taux d’erreur.'
	},
	'Outils et sources de vérité': {
		outcomes: ['efficacite', 'connaissance', 'qualite'],
		purpose: 'Savoir où lire la bonne donnée et éviter les réponses fondées sur une source obsolète.',
		decision: 'Choisir la source fiable et l’intégration nécessaire.',
		workflow: 'Lire la source de vérité avant de préparer une action.',
		metric: 'Erreurs de données ou temps de recherche.'
	},
	'Pertes, risques et priorités': {
		outcomes: ['revenus', 'efficacite', 'risques'],
		purpose: 'Concentrer LunarIA sur les problèmes qui ont le plus d’impact.',
		decision: 'Prioriser le premier problème ou risque à traiter.',
		workflow: 'Détecter la perte, alerter et préparer une correction.',
		metric: 'Montant, temps ou incidents évités.'
	},
	'Objectifs et indicateurs': {
		outcomes: ['revenus', 'clients', 'efficacite', 'qualite', 'risques'],
		purpose: 'Mesurer si les actions de LunarIA produisent réellement un résultat.',
		decision: 'Poursuivre, corriger ou arrêter une action.',
		workflow: 'Mesurer le résultat après chaque action validée.',
		metric: 'Indicateur choisi par l’entreprise.'
	},
	'Règles et permissions': {
		outcomes: ['risques', 'qualite'],
		purpose: 'Encadrer l’autonomie de LunarIA et éviter une action non autorisée.',
		decision: 'Déterminer ce qui exige une validation humaine.',
		workflow: 'Bloquer, demander validation puis journaliser l’action.',
		metric: 'Actions sensibles validées et incidents évités.'
	}
};

const selectedOutcomeIds = (goals: BusinessGoal[]) =>
	new Set<BusinessOutcomeId>(goals.map((goal) => goal.outcomeId));

export const enrichFactsWithUtility = (
	facts: EvidenceFact[],
	goals: BusinessGoal[] = []
): EvidenceFact[] => {
	const selected = selectedOutcomeIds(goals);
	return facts.map((fact) => {
		const base = SECTION_UTILITY[fact.section] ?? SECTION_UTILITY['Processus et tâches'];
		const goalMatch = base.outcomes.some((outcome) => selected.has(outcome));
		const sourceWeight =
			fact.sourceType === 'dirigeant' || fact.sourceType === 'integration'
				? 0.14
				: fact.sourceType === 'document'
					? 0.12
					: fact.sourceType === 'site'
						? 0.08
						: 0;
		const concreteWeight = /\d|%|€|euro|heure|jour|client|revenu|coût|risque/i.test(fact.value)
			? 0.07
			: 0;
		const priority = Math.min(
			1,
			0.46 + (goalMatch ? 0.24 : 0) + sourceWeight + concreteWeight + fact.confidence * 0.08
		);
		return {
			...fact,
			utility: {
				outcomeIds: base.outcomes,
				purpose: base.purpose,
				decision: base.decision,
				workflowHint: base.workflow,
				metricHint: base.metric,
				priority
			}
		};
	});
};

const similarEnough = (first: EvidenceFact, second: EvidenceFact) => {
	const words = (value: string) =>
		new Set(
			value
				.toLowerCase()
				.normalize('NFD')
				.replace(/[\u0300-\u036f]/g, '')
				.split(/[^a-z0-9]+/)
				.filter((word) => word.length >= 5)
		);
	const a = words(`${first.label} ${first.value}`);
	const b = words(`${second.label} ${second.value}`);
	if (!a.size || !b.size) return false;
	const overlap = [...a].filter((word) => b.has(word)).length;
	return overlap / Math.min(a.size, b.size) >= 0.65;
};

export const buildExecutiveFacts = (
	facts: EvidenceFact[],
	goals: BusinessGoal[] = [],
	limit = 15
) => {
	const enriched = enrichFactsWithUtility(facts, goals);
	const selected: EvidenceFact[] = [];
	for (const group of EXECUTIVE_GROUPS) {
		const candidates = enriched
			.filter((fact) => group.sections.includes(fact.section))
			.sort(
				(a, b) =>
					(b.utility?.priority ?? 0) - (a.utility?.priority ?? 0) ||
					b.confidence - a.confidence
			);
		const groupFacts: EvidenceFact[] = [];
		for (const fact of candidates) {
			if (groupFacts.length >= 3) break;
			if ([...selected, ...groupFacts].some((candidate) => similarEnough(candidate, fact))) continue;
			groupFacts.push(fact);
		}
		selected.push(...groupFacts);
	}
	return selected
		.sort(
			(a, b) =>
				(b.utility?.priority ?? 0) - (a.utility?.priority ?? 0) || b.confidence - a.confidence
		)
		.slice(0, Math.max(1, Math.min(15, limit)));
};

const publicHypothesis = (facts: EvidenceFact[], section: string, labels: string[]) =>
	facts.find(
		(fact) =>
			fact.section === section &&
			labels.some((label) => fact.label.toLowerCase().includes(label.toLowerCase()))
	)?.value ?? '';

export const buildInterviewQuestions = (
	facts: EvidenceFact[],
	goals: BusinessGoal[] = []
): InterviewQuestion[] => {
	const icp = publicHypothesis(facts, 'Clients et ICP', ['client', 'icp', 'cible']);
	const offer = publicHypothesis(facts, 'Offres et positionnement', [
		'offre',
		'activité',
		'service'
	]);
	const priority = publicHypothesis(facts, 'Pertes, risques et priorités', ['priorité actuelle']);
	const timeLoss = publicHypothesis(facts, 'Pertes, risques et priorités', [
		'principale perte de temps'
	]);
	const tools = publicHypothesis(facts, 'Outils et sources de vérité', ['outils du quotidien']);
	const knownName = publicHypothesis(facts, 'Identité et modèle économique', ['nom', 'entreprise']);
	const goalSummary = goals.map((goal) => goal.label).join(' · ');
	const questions: InterviewQuestion[] = [
		...(knownName
			? []
			: [
					{
						id: 'nom-entreprise',
						section: 'Identité et modèle économique',
						label: "Nom de l'entreprise",
						prompt: 'Quel est le nom de votre entreprise ?',
						helper: 'Le nom utilisé avec vos clients.',
						placeholder: 'Nom de votre entreprise',
						optional: false
					}
				]),
		{
			id: 'modele-economique',
			section: 'Identité et modèle économique',
			label: 'Modèle économique réel',
			prompt: 'Comment votre entreprise gagne-t-elle réellement de l’argent ?',
			helper: offer
				? `J’ai trouvé cette offre publique : « ${offer} ». Expliquez-moi maintenant ce qui génère vraiment votre chiffre d’affaires.`
				: 'Décrivez les revenus réels : abonnement, devis, commission, vente, prestation…',
			placeholder: 'Ex. 70 % par abonnement mensuel, 30 % par installation…',
			optional: false
		},
		{
			id: 'clients-reels',
			section: 'Clients et ICP',
			label: 'Clients réels et rentables',
			prompt: 'Qui sont aujourd’hui vos meilleurs clients ?',
			helper: icp
				? `Le Web laisse penser que votre cible est : « ${icp} ». Confirmez, corrigez ou précisez.`
				: 'Parlez des clients qui achètent réellement, restent et sont rentables.',
			placeholder: 'Secteur, taille, localisation, comportement d’achat…',
			optional: false
		},
		{
			id: 'priorite',
			section: 'Pertes, risques et priorités',
			label: 'Résultat attendu à 90 jours',
			prompt: 'À quoi verrez-vous, dans 90 jours, que LunarIA vous a réellement aidé ?',
			helper: goalSummary
				? `Vous avez choisi : « ${goalSummary} ». Donnez maintenant un résultat concret et observable.`
				: 'Formulez un résultat concret et observable, pas une technologie.',
			placeholder: 'Ex. délai réduit, opportunités traitées, qualité stabilisée…',
			optional: false
		},
		{
			id: 'perte-argent',
			section: 'Pertes, risques et priorités',
			label: 'Principale perte d’argent',
			prompt: 'Où votre entreprise perd-elle le plus d’argent aujourd’hui ?',
			helper: 'Impayés, prospects oubliés, erreurs, temps non facturé, stock, churn…',
			placeholder: 'Décrivez un problème concret et sa fréquence.',
			optional: true
		},
		{
			id: 'perte-temps',
			section: 'Pertes, risques et priorités',
			label: 'Principale perte de temps',
			prompt: 'Quelle tâche vous fait perdre le plus de temps chaque semaine ?',
			helper: 'Cherchez une tâche répétitive, mesurable et pénible.',
			placeholder: 'Ex. 8 h par semaine à relancer, recopier ou rechercher…',
			optional: false
		},
		{
			id: 'taches-recurrentes',
			section: 'Processus et tâches',
			label: 'Processus et tâches récurrents',
			prompt: 'Quels processus ou tâches répétitives pèsent le plus sur vos objectifs ?',
			helper: timeLoss
				? `Vous venez d’identifier cette perte de temps : « ${timeLoss} ». Quelles tâches concrètes l’alimentent ?`
				: 'Une tâche par ligne. Pensez au quotidien et à l’hebdomadaire.',
			placeholder: 'Relancer les factures\nTrier les demandes\nPréparer le brief du lundi',
			optional: false
		},
		{
			id: 'decisions',
			section: 'Processus et tâches',
			label: 'Décisions récurrentes',
			prompt: 'Quelles décisions reviennent toujours jusqu’à vous ?',
			helper: 'Celles qui ralentissent l’équipe ou dépendent encore du dirigeant.',
			placeholder: 'Ex. remise commerciale, priorité client, validation d’un paiement…',
			optional: true
		},
		{
			id: 'messages',
			section: 'Processus et tâches',
			label: 'Messages et demandes récurrents',
			prompt: 'Quels messages ou demandes recevez-vous constamment ?',
			helper: 'Clients, prospects, salariés, fournisseurs ou partenaires.',
			placeholder: 'Ex. demandes de prix, suivi de commande, questions SAV…',
			optional: true
		},
		{
			id: 'recherches',
			section: 'Processus et tâches',
			label: 'Recherches récurrentes',
			prompt: 'Quelles informations recherchez-vous régulièrement ?',
			helper: 'Web, documents internes, clients, marché, réglementation…',
			placeholder: 'Ex. nouveaux prospects, tarifs concurrents, dossier d’un client…',
			optional: true
		},
		{
			id: 'planning',
			section: 'Processus et tâches',
			label: 'Planification actuelle',
			prompt: 'Comment organisez-vous actuellement vos priorités et votre planning ?',
			helper: 'Dites la réalité, même si elle tient dans votre tête ou sur du papier.',
			placeholder: 'Agenda, Excel, CRM, post-it, réunions, rien de formalisé…',
			optional: true
		},
		{
			id: 'outils',
			section: 'Outils et sources de vérité',
			label: 'Outils du quotidien',
			prompt: 'Où se trouvent vos informations importantes et quelle source fait foi ?',
			helper: 'Citez les outils, fichiers ou personnes, puis indiquez la source fiable en cas de conflit.',
			placeholder: 'Information → outil ou source de vérité',
			optional: false
		},
		{
			id: 'documents',
			section: 'Outils et sources de vérité',
			label: 'Documents importants',
			prompt: 'Quels documents LunarIA devra-t-elle connaître pour bien travailler ?',
			helper: priority
				? `Pour atteindre « ${priority} », quels fichiers, procédures, contrats ou modèles font foi ?`
				: 'Procédures, contrats, catalogues, modèles, tableaux, comptes rendus…',
			placeholder: 'Document → contenu utile → emplacement actuel',
			optional: true
		},
		{
			id: 'sources-verite',
			section: 'Outils et sources de vérité',
			label: 'Sources de vérité',
			prompt: 'Quand deux informations se contredisent, quel outil fait foi ?',
			helper: tools
				? `Vous avez cité : « ${tools} ». Précisez maintenant quelle source fait foi pour chaque donnée.`
				: 'Ex. la comptabilité pour les factures, le CRM pour les prospects.',
			placeholder: 'Donnée → outil de référence',
			optional: true
		},
		{
			id: 'responsables',
			section: 'Organisation et responsabilités',
			label: 'Responsables clés',
			prompt: 'Qui est responsable de quoi dans votre entreprise ?',
			helper: 'Prénom ou rôle, puis responsabilité. Une ligne par personne ou équipe.',
			placeholder: 'Marie → facturation\nPaul → commerce\nDirection → remises',
			optional: true
		},
		{
			id: 'indicateurs',
			section: 'Objectifs et indicateurs',
			label: 'Indicateurs de réussite',
			prompt: 'Quels chiffres vous disent que l’entreprise va bien ?',
			helper: 'Choisissez les indicateurs que vous regardez réellement.',
			placeholder: 'Trésorerie, CA, délai de paiement, leads, conversion, satisfaction…',
			optional: false
		},
		{
			id: 'validation',
			section: 'Règles et permissions',
			label: 'Actions soumises à validation',
			prompt: 'Quelles actions LunarIA devra-t-elle toujours vous faire valider ?',
			helper: 'Pensez aux actions coûteuses, sensibles ou difficiles à annuler.',
			placeholder: 'Envoyer un email externe, accorder une remise, modifier une facture…',
			optional: false
		},
		{
			id: 'interdictions',
			section: 'Règles et permissions',
			label: 'Interdictions absolues',
			prompt: 'Qu’est-ce que LunarIA n’aura jamais le droit de faire ?',
			helper: 'Ces règles deviendront les limites écrites de votre AgentOS.',
			placeholder: 'Ex. payer, supprimer, publier ou envoyer sans autorisation…',
			optional: false
		},
		{
			id: 'premiere-delegation',
			section: 'Pertes, risques et priorités',
			label: 'Première mission souhaitée',
			prompt: 'Si LunarIA pouvait prendre une seule mission dès demain, laquelle choisiriez-vous ?',
			helper: 'Choisissez un résultat utile, pas une technologie.',
			placeholder: 'Ex. récupérer mes impayés, préparer mes rendez-vous…',
			optional: false
		}
	];
	const usefulQuestionIds = new Set([
		'nom-entreprise',
		'modele-economique',
		'clients-reels',
		'priorite',
		'perte-temps',
		'taches-recurrentes',
		'outils',
		'responsables',
		'indicateurs',
		'validation',
		'interdictions',
		'premiere-delegation'
	]);
	return questions.filter((question) => usefulQuestionIds.has(question.id)).slice(0, 12);
};

export const answerToFact = (
	question: InterviewQuestion,
	answer: InterviewAnswer
): EvidenceFact | null => {
	const value = compact(answer.value ?? '');
	if (!value || answer.skipped) return null;
	return {
		id: `dirigeant-${safeId(question.id)}`,
		section: question.section,
		label: question.label,
		value,
		sourceType: 'dirigeant',
		observedAt: today(),
		status: 'confirme',
		confidence: 1
	};
};

export const provenanceLabel = (fact: EvidenceFact) => {
	if (fact.sourceType === 'dirigeant') return 'Confirmé par le dirigeant';
	if (fact.sourceType === 'site') return 'Déclaré sur le site de l’entreprise';
	if (fact.sourceType === 'web') return 'Source extérieure — à vérifier';
	if (fact.sourceType === 'document') return 'Document interne';
	return 'Donnée connectée';
};

export const sourceQualityLabel = (fact: EvidenceFact, companySiteUrl = '') => {
	if (fact.sourceType === 'dirigeant') return 'Source directe';
	if (fact.sourceType === 'document') return 'Source interne';
	if (fact.sourceType === 'integration') return 'Donnée opérationnelle';
	if (fact.sourceType === 'site') return 'Déclaration de l’entreprise';
	try {
		const sourceHost = new URL(fact.sourceUrl ?? '').hostname.replace(/^www\./, '');
		const companyHost = new URL(companySiteUrl).hostname.replace(/^www\./, '');
		if (sourceHost && companyHost && sourceHost === companyHost) return 'Source directe extérieure';
	} catch {
		// Une URL absente ou invalide reste une source tierce à vérifier.
	}
	return 'Source tierce — à recouper';
};

export const statusLabel = (fact: EvidenceFact) => {
	if (fact.status === 'confirme') return 'Confirmé';
	if (fact.status === 'corrige') return 'Corrigé par le dirigeant';
	if (fact.status === 'non_recherche') return 'Non recherché';
	return 'À confirmer';
};

export const factsBySection = (facts: EvidenceFact[]) =>
	SECTION_ORDER.map((section) => ({
		section,
		facts: facts.filter((fact) => fact.section === section)
	})).filter((group) => group.facts.length > 0);

const markdownValue = (value: string) => value.replace(/\r/g, '').trim();

export const buildMapMarkdown = (map: OperationalMap): string => {
	const executiveIds = new Set(
		buildExecutiveFacts(map.facts, map.goals ?? []).map((fact) => fact.id)
	);
	const operationalFacts = map.facts.filter(
		(fact) =>
			executiveIds.has(fact.id) ||
			fact.sourceType === 'dirigeant' ||
			fact.sourceType === 'document' ||
			fact.sourceType === 'integration' ||
			fact.status === 'corrige'
	);
	const evidenceOnly = map.facts.filter((fact) => !operationalFacts.some((item) => item.id === fact.id));
	const lines = [
		'# Carte opérationnelle de l’entreprise',
		'',
		`- Entreprise : ${map.companyName || 'À compléter'}`,
		`- Site : ${map.siteUrl || 'Non renseigné'}`,
		`- Validée le : ${map.validatedAt || today()}`,
		''
	];
	if (map.goals?.length) {
		lines.push('## Résultats prioritaires à 90 jours', '');
		for (const goal of map.goals) {
			lines.push(`- ${goal.label}${goal.detail ? ` — ${goal.detail}` : ''}`);
		}
		lines.push('');
	}
	for (const group of factsBySection(operationalFacts)) {
		lines.push(`## ${group.section}`, '');
		for (const fact of group.facts) {
			lines.push(`### ${fact.label}`, '', markdownValue(fact.value), '');
			lines.push(`- Statut : ${statusLabel(fact)}`);
			lines.push(`- Provenance : ${provenanceLabel(fact)}`);
			if (fact.utility) {
				lines.push(`- Utilité : ${fact.utility.purpose}`);
				lines.push(`- Décision concernée : ${fact.utility.decision}`);
				lines.push(`- Workflow possible : ${fact.utility.workflowHint}`);
				lines.push(`- Mesure possible : ${fact.utility.metricHint}`);
			}
			lines.push(`- Dernière vérification : ${fact.observedAt}`);
			if (fact.sourceTitle) lines.push(`- Source : ${fact.sourceTitle}`);
			if (fact.sourceUrl) lines.push(`- URL : ${fact.sourceUrl}`);
			lines.push('');
		}
	}
	if (evidenceOnly.length) {
		lines.push('## Annexe — preuves conservées en profondeur', '');
		lines.push(
			'Ces éléments restent consultables avec leur provenance mais ne pilotent pas directement les actions.',
			''
		);
		for (const fact of evidenceOnly) {
			lines.push(`- **${fact.label}** — ${markdownValue(fact.value)}`);
			lines.push(`  - Provenance : ${provenanceLabel(fact)} · ${fact.observedAt}`);
			if (fact.sourceUrl) lines.push(`  - URL : ${fact.sourceUrl}`);
		}
		lines.push('');
	}
	return lines.join('\n').trim() + '\n';
};

export const buildWorkflowMarkdown = (workflow: WorkflowProposal): string =>
	[
		`# ${workflow.title}`,
		'',
		`- Problème : ${workflow.problem}`,
		`- Impact attendu : ${workflow.impact}`,
		`- Déclencheur : ${workflow.trigger}`,
		`- Responsable : ${workflow.owner}`,
		`- Porte humaine : ${workflow.humanGate}`,
		`- Indicateur : ${workflow.metric}`,
		`- Première échéance : ${workflow.deadline}`,
		`- Confiance : ${Math.round(workflow.confidence * 100)} %`,
		'',
		'## Boucle',
		'',
		...workflow.steps.map((step, index) => `${index + 1}. ${step}`),
		'',
		'## Données nécessaires',
		'',
		...workflow.dataNeeded.map((item) => `- ${item}`),
		'',
		'## Intégrations',
		'',
		...(workflow.integrations.length
			? workflow.integrations.map((item) => `- ${item}`)
			: ['- Aucune intégration indispensable au premier palier']),
		'',
		'## Ce que LunarIA peut préparer seule',
		'',
		...(workflow.autonomousActions.length
			? workflow.autonomousActions.map((item) => `- ${item}`)
			: ['- Rien sans validation pour ce premier palier']),
		'',
		'## Interdictions',
		'',
		...workflow.forbidden.map((item) => `- ${item}`)
	].join('\n');

export const integrationSearchTerm = (name: string) => {
	const lower = name.toLowerCase();
	if (lower.includes('google') || lower.includes('gmail')) return 'google-workspace';
	if (lower.includes('microsoft') || lower.includes('outlook')) return 'microsoft-365';
	if (lower.includes('notion')) return 'notion';
	if (lower.includes('airtable')) return 'airtable';
	if (lower.includes('calendly')) return 'calendly';
	if (lower.includes('obsidian')) return 'obsidian';
	return name.trim();
};
