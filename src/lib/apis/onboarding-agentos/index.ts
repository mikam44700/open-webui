import { WEBUI_API_BASE_URL } from '$lib/constants';
import {
	buildExecutiveFacts,
	buildExternalSearchQueries,
	deduplicateSimilarFacts,
	diversifyExternalFactsByDomain,
	filterAndDiversifyExternalItems,
	normalizeFacts,
	safeId
} from '$lib/onboarding-agentos/logic';
import type {
	BusinessGoal,
	EvidenceFact,
	ExternalBusinessSignal,
	ExternalSearchItem,
	OperationalMap,
	WorkflowProposal
} from '$lib/onboarding-agentos/types';

export type CrawlResult = {
	status: 'reussi' | 'partiel' | 'echec';
	markdown: string;
	chars: number;
	message?: string | null;
	url: string;
	pages?: string[];
};

const readableErrorDetail = (detail: unknown): string => {
	if (typeof detail === 'string' && detail.trim()) return detail.trim();
	if (Array.isArray(detail)) {
		const messages = detail
			.map((item) =>
				typeof item === 'object' && item !== null && 'msg' in item
					? String((item as { msg?: unknown }).msg ?? '')
					: readableErrorDetail(item)
			)
			.filter(Boolean);
		return messages.join(' ');
	}
	if (typeof detail === 'object' && detail !== null) {
		const record = detail as Record<string, unknown>;
		return readableErrorDetail(record.message ?? record.error ?? '');
	}
	return '';
};

const responseError = async (response: Response, fallback: string) => {
	try {
		const body = await response.json();
		return readableErrorDetail(body?.detail) || readableErrorDetail(body) || fallback;
	} catch {
		return fallback;
	}
};

const jsonFromText = (text: string): any => {
	const trimmed = text
		.trim()
		.replace(/^```(?:json)?\s*/i, '')
		.replace(/\s*```$/, '');
	const objectStart = trimmed.indexOf('{');
	const arrayStart = trimmed.indexOf('[');
	const start =
		objectStart < 0 ? arrayStart : arrayStart < 0 ? objectStart : Math.min(objectStart, arrayStart);
	const objectEnd = trimmed.lastIndexOf('}');
	const arrayEnd = trimmed.lastIndexOf(']');
	const end = Math.max(objectEnd, arrayEnd);
	if (start < 0 || end < start) throw new Error('Réponse structurée introuvable.');
	return JSON.parse(trimmed.slice(start, end + 1));
};

const callStructuredModel = async (
	token: string,
	providerId: string,
	modelId: string,
	system: string,
	user: string
) => {
	if (!providerId || !modelId) throw new Error("Aucun modèle IA n'est actif.");
	const response = await fetch(`${WEBUI_API_BASE_URL}/onboarding/structured`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			provider_id: providerId,
			model_id: modelId,
			system,
			user
		})
	});
	if (!response.ok) {
		throw new Error(String(await responseError(response, "Le cerveau IA n'a pas répondu.")));
	}
	const payload = await response.json();
	return jsonFromText(String(payload?.content ?? ''));
};

export const crawlCompanySite = async (token: string, url: string): Promise<CrawlResult> => {
	try {
		const response = await fetch(`${WEBUI_API_BASE_URL}/onboarding/crawl`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ url, mode: 'quality' })
		});
		if (!response.ok) {
			return {
				status: 'echec',
				markdown: '',
				chars: 0,
				url,
				pages: [],
				message: String(await responseError(response, "Le site n'a pas pu être analysé."))
			};
		}
		return (await response.json()) as CrawlResult;
	} catch {
		return {
			status: 'echec',
			markdown: '',
			chars: 0,
			url,
			pages: [],
			message: "Le site n'a pas pu être analysé."
		};
	}
};

const SITE_SYSTEM = `Tu construis la carte opérationnelle factuelle d'une entreprise à partir
du contenu de SON site. Réponds uniquement en JSON valide :
{"companyName":"...","facts":[{"id":"site-...","section":"...","label":"...","value":"...",
"sourceUrl":"URL exacte parmi les pages autorisées","confidence":0.0}]}

Sections autorisées :
- Identité et modèle économique
- Offres et positionnement
- Clients et ICP
- Réputation et signaux

Extrais uniquement ce que le site affirme : identité, activité, modèle économique visible,
offres, services, prix, clientèle annoncée, problèmes résolus, vocabulaire, ton, preuves,
coordonnées, équipe et implantations. Une idée par fait. Ne transforme jamais une hypothèse
en certitude. N'invente ni chiffre, ni client, ni revenu, ni concurrent. Le statut et la date
seront ajoutés par le produit.`;

export const synthesizeSiteFacts = async (
	token: string,
	providerId: string,
	modelId: string,
	crawl: CrawlResult
): Promise<{ companyName: string; facts: EvidenceFact[] }> => {
	const pages = crawl.pages?.length ? crawl.pages : [crawl.url];
	const payload = await callStructuredModel(
		token,
		providerId,
		modelId,
		SITE_SYSTEM,
		`Pages autorisées :\n${pages.map((page) => `- ${page}`).join('\n')}\n\nContenu :\n${crawl.markdown.slice(0, 32000)}`
	);
	const allowed = new Set(pages);
	const facts = normalizeFacts(Array.isArray(payload?.facts) ? payload.facts : [], 'site').map(
		(fact, index) => ({
			...fact,
			id: fact.id.startsWith('site-') ? fact.id : `site-${safeId(fact.label)}-${index + 1}`,
			sourceType: 'site' as const,
			sourceUrl: allowed.has(fact.sourceUrl ?? '') ? fact.sourceUrl : crawl.url,
			status: 'a_confirmer' as const
		})
	);
	return { companyName: String(payload?.companyName ?? '').trim(), facts };
};

const serializeSearchItems = (data: any): ExternalSearchItem[] => {
	const raw = Array.isArray(data?.items) ? data.items : [];
	const seen = new Set<string>();
	const items: ExternalSearchItem[] = [];
	for (const item of raw) {
		const link = String(item?.link ?? item?.url ?? '').trim();
		if (!link || seen.has(link)) continue;
		seen.add(link);
		items.push({
			title: String(item?.title ?? link).trim(),
			link,
			snippet: String(item?.snippet ?? item?.content ?? '')
				.trim()
				.slice(0, 3000),
			publishedDate: item?.published_date ?? item?.publishedDate ?? null
		});
	}
	if (items.length) return items;
	for (const doc of Array.isArray(data?.docs) ? data.docs : []) {
		const link = String(doc?.metadata?.source ?? '').trim();
		if (!link || seen.has(link)) continue;
		seen.add(link);
		items.push({
			title: String(doc?.metadata?.title ?? link).trim(),
			link,
			snippet: String(doc?.metadata?.snippet ?? doc?.content ?? '')
				.trim()
				.slice(0, 3000)
		});
	}
	return items;
};

export const searchCompanyWeb = async (
	token: string,
	webProvider: string,
	context: {
		companyName: string;
		siteUrl: string;
		sectorHint?: string;
		offerHint?: string;
		icpHint?: string;
		problemHint?: string;
		goals?: BusinessGoal[];
	}
): Promise<ExternalSearchItem[]> => {
	const queries = buildExternalSearchQueries(context);
	const response = await fetch(`${WEBUI_API_BASE_URL}/onboarding/web-search`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ provider: webProvider, queries })
	});
	if (!response.ok)
		throw new Error(String(await responseError(response, 'Recherche Web indisponible.')));
	return filterAndDiversifyExternalItems(
		serializeSearchItems(await response.json()),
		context.siteUrl
	);
};

const WEB_SYSTEM = `Tu analyses ce que le Web extérieur dit d'une entreprise. Réponds uniquement
en JSON valide : {"facts":[{"id":"web-...","section":"...","label":"...","value":"...",
"sourceUrl":"URL exacte fournie","sourceTitle":"titre exact","confidence":0.0,
"signalType":"opportunite|risque|besoin_client|mouvement_concurrent|signal_marche",
"goalId":"identifiant exact d'une priorité fournie","whyItMatters":"...",
"nextAction":"prochaine décision ou action préparatoire..."}]}

Sections autorisées :
- Clients et ICP
- Concurrence et marché
- Réputation et signaux

Construis au maximum douze faits utiles pour cinq axes : besoins clients supposés, concurrents
directs ou indirects, réputation extérieure, contexte de marché et signaux récents. Chaque fait
doit être soutenu par UNE URL exacte de la liste et relié à UNE priorité à 90 jours fournie.
"whyItMatters" explique concrètement le lien avec cette priorité. "nextAction" propose une décision
ou une action préparatoire réaliste, jamais une exécution automatique. Écris "hypothèse", "supposé"
ou "semble" pour toute déduction. Ne reprends pas un extrait parlant d'une autre entreprise.
N'invente jamais de gain financier, de chiffre, de client, de santé financière ou de capacité
interne. Ignore les résultats ambigus, les annuaires sans contenu et les preuves faibles.`;

export const synthesizeWebFacts = async (
	token: string,
	providerId: string,
	modelId: string,
	items: ExternalSearchItem[],
	context: {
		companyName: string;
		siteUrl: string;
		goals: BusinessGoal[];
	}
): Promise<EvidenceFact[]> => {
	if (!items.length) return [];
	// Le moteur Web peut renvoyer plus de 30 résultats avec des extraits très longs.
	// On conserve un échantillon diversifié et compact pour rester sous la limite stricte
	// de l'endpoint de synthèse sans sacrifier les URLs de preuve.
	const sources = items.slice(0, 20).map((item, index) => ({
		index: index + 1,
		title: item.title.slice(0, 250),
		url: item.link.slice(0, 1_000),
		snippet: item.snippet.slice(0, 1_100),
		publishedDate: item.publishedDate
	}));
	const payload = await callStructuredModel(
		token,
		providerId,
		modelId,
		WEB_SYSTEM,
		JSON.stringify({
			companyName: context.companyName,
			companyDomain: new URL(context.siteUrl).hostname.replace(/^www\./, ''),
			priorities90Days: context.goals,
			externalSources: sources
		})
	);
	const byUrl = new Map(sources.map((source) => [source.url, source]));
	const allowedGoalIds = new Set(context.goals.map((goal) => goal.id));
	const rawFacts = (Array.isArray(payload?.facts) ? payload.facts : []).map((fact: any) => {
		const kind = String(fact?.signalType ?? '').trim() as ExternalBusinessSignal['kind'];
		const goalId = String(fact?.goalId ?? '').trim();
		return {
			...fact,
			businessSignal: allowedGoalIds.has(goalId)
				? {
						kind,
						goalId,
						whyItMatters: String(fact?.whyItMatters ?? '').trim(),
						nextAction: String(fact?.nextAction ?? '').trim()
					}
				: undefined
		};
	});
	const normalized = normalizeFacts(rawFacts, 'web')
		.filter((fact) => byUrl.has(fact.sourceUrl ?? ''))
		.map((fact, index) => {
			const source = byUrl.get(fact.sourceUrl ?? '')!;
			return {
				...fact,
				id: fact.id.startsWith('web-') ? fact.id : `web-${safeId(fact.label)}-${index + 1}`,
				sourceType: 'web' as const,
				sourceTitle: source.title,
				status: 'a_confirmer' as const
			};
		});
	const diversified = diversifyExternalFactsByDomain(deduplicateSimilarFacts(normalized), 3, 12);
	if (context.goals.length && !diversified.some((fact) => fact.businessSignal)) {
		throw new Error(
			"Le Web extérieur n'a produit aucun signal exploitable pour vos priorités. Relancez l'analyse."
		);
	}
	return diversified;
};

const WORKFLOW_SYSTEM = `Tu es le concepteur opérationnel de LunarIA. À partir d'une carte
d'entreprise validée, propose entre 1 et 3 workflows maximum. Réponds uniquement en JSON valide :
{"workflows":[{
"id":"workflow-...",
"title":"...",
"problem":"problème précis observé",
"impact":"impact attendu sans inventer de chiffre",
"trigger":"événement exact qui lance la boucle",
"steps":["Détecter ...","Comprendre ...","Préparer ...","Vérifier ...","Faire valider ...","Agir ...","Mesurer ..."],
"dataNeeded":["..."],
"integrations":["nom compréhensible de l'application"],
"autonomousActions":["actions préparatoires que LunarIA peut faire sans effet externe"],
"owner":"rôle côté entreprise",
"humanGate":"validation exacte exigée",
"forbidden":["actions interdites"],
"metric":"indicateur mesurable",
"deadline":"première échéance réaliste",
"confidence":0.0,
"evidenceFactIds":["identifiants de faits fournis"]
}]}

Règles : rattache chaque workflow à des faits existants ; jamais de recommandation vague ;
ne promets pas une intégration absente ; ne prétends pas exécuter le workflow maintenant ;
toute action externe, financière, destructive ou de publication exige une porte humaine ;
classe les propositions de la plus forte valeur/faisabilité à la plus faible ; privilégie le
résultat financier ou le temps récupéré ; si les preuves sont insuffisantes, propose moins de
workflows avec une confiance plus basse.`;

const stringList = (value: unknown, fallback: string[] = []) =>
	Array.isArray(value) ? value.map((item) => String(item).trim()).filter(Boolean) : fallback;

export const generateWorkflowProposals = async (
	token: string,
	providerId: string,
	modelId: string,
	map: OperationalMap
): Promise<WorkflowProposal[]> => {
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
	const payload = await callStructuredModel(
		token,
		providerId,
		modelId,
		WORKFLOW_SYSTEM,
		JSON.stringify({
			companyName: map.companyName,
			goals: map.goals ?? [],
			facts: operationalFacts.map((fact) => ({
				id: fact.id,
				section: fact.section,
				label: fact.label,
				value: fact.value,
				status: fact.status,
				utility: fact.utility
			}))
		})
	);
	const allowedFactIds = new Set(operationalFacts.map((fact) => fact.id));
	const raw = Array.isArray(payload?.workflows) ? payload.workflows.slice(0, 3) : [];
	return raw
		.map((workflow: any, index: number): WorkflowProposal => {
			const title = String(workflow?.title ?? '').trim();
			return {
				id: String(workflow?.id ?? '').trim() || `workflow-${safeId(title)}-${index + 1}`,
				title,
				problem: String(workflow?.problem ?? '').trim(),
				impact: String(workflow?.impact ?? '').trim(),
				trigger: String(workflow?.trigger ?? '').trim(),
				steps: stringList(workflow?.steps),
				dataNeeded: stringList(workflow?.dataNeeded),
				integrations: stringList(workflow?.integrations),
				autonomousActions: stringList(workflow?.autonomousActions),
				owner: String(workflow?.owner ?? 'Direction').trim(),
				humanGate: String(workflow?.humanGate ?? 'Validation du dirigeant avant action').trim(),
				forbidden: stringList(workflow?.forbidden, ['Aucune action irréversible sans validation']),
				metric: String(workflow?.metric ?? '').trim(),
				deadline: String(workflow?.deadline ?? 'À définir avec le dirigeant').trim(),
				confidence: Math.max(0, Math.min(1, Number(workflow?.confidence ?? 0.5))),
				evidenceFactIds: stringList(workflow?.evidenceFactIds).filter((id) =>
					allowedFactIds.has(id)
				)
			};
		})
		.filter(
			(workflow: WorkflowProposal) =>
				workflow.title &&
				workflow.problem &&
				workflow.impact &&
				workflow.trigger &&
				workflow.metric &&
				workflow.steps.length >= 4 &&
				workflow.dataNeeded.length >= 1 &&
				workflow.autonomousActions.length >= 1 &&
				workflow.evidenceFactIds.length >= 1
		);
};

export const initMemoryVault = async (token: string) => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/memory/init`, {
		method: 'POST',
		headers: { Authorization: `Bearer ${token}` }
	});
	if (!response.ok) throw new Error(String(await responseError(response, 'Mémoire indisponible.')));
	return response.json();
};

export const saveManagedNote = async (
	token: string,
	noteId: string,
	title: string,
	content: string
) => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/memory/managed-note`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ note_id: noteId, title, content })
	});
	if (!response.ok)
		throw new Error(String(await responseError(response, "Échec de l'enregistrement.")));
	return response.json();
};
