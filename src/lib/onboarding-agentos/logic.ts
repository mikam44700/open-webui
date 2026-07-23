import type {
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

const publicHypothesis = (facts: EvidenceFact[], section: string, labels: string[]) =>
	facts.find(
		(fact) =>
			fact.section === section &&
			labels.some((label) => fact.label.toLowerCase().includes(label.toLowerCase()))
	)?.value ?? '';

export const buildInterviewQuestions = (facts: EvidenceFact[]): InterviewQuestion[] => {
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
			label: 'Priorité actuelle',
			prompt: 'Quelle est votre priorité numéro 1 pour les trois prochains mois ?',
			helper: 'Une seule priorité, formulée comme un résultat concret.',
			placeholder: 'Ex. réduire les impayés de 30 %, signer 10 nouveaux clients…',
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
			label: 'Tâches récurrentes',
			prompt: 'Quelles sont les trois à cinq tâches que vous répétez le plus souvent ?',
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
			prompt: 'Quels outils contiennent aujourd’hui vos informations importantes ?',
			helper: 'Comptabilité, CRM, email, agenda, fichiers, support, facturation…',
			placeholder: 'Un outil par ligne, avec ce qu’il contient.',
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
	return questions;
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
	if (fact.sourceType === 'site') return 'Trouvé sur le site';
	if (fact.sourceType === 'web') return 'Source Web extérieure';
	if (fact.sourceType === 'document') return 'Document interne';
	return 'Donnée connectée';
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
	const lines = [
		'# Carte opérationnelle de l’entreprise',
		'',
		`- Entreprise : ${map.companyName || 'À compléter'}`,
		`- Site : ${map.siteUrl || 'Non renseigné'}`,
		`- Validée le : ${map.validatedAt || today()}`,
		''
	];
	for (const group of factsBySection(map.facts)) {
		lines.push(`## ${group.section}`, '');
		for (const fact of group.facts) {
			lines.push(`### ${fact.label}`, '', markdownValue(fact.value), '');
			lines.push(`- Statut : ${statusLabel(fact)}`);
			lines.push(`- Provenance : ${provenanceLabel(fact)}`);
			lines.push(`- Dernière vérification : ${fact.observedAt}`);
			if (fact.sourceTitle) lines.push(`- Source : ${fact.sourceTitle}`);
			if (fact.sourceUrl) lines.push(`- URL : ${fact.sourceUrl}`);
			lines.push('');
		}
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
