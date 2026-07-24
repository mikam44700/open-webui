import { WEBUI_API_BASE_URL } from '$lib/constants';
import {
	buildExecutiveFacts,
	buildExternalSearchQueries,
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
	user: string,
	options: { maxTokens?: number; timeoutSeconds?: number } = {}
) => {
	if (!providerId || !modelId) throw new Error("Aucun modèle IA n'est actif.");
	const timeoutSeconds = options.timeoutSeconds ?? 90;
	let response: Response;
	try {
		response = await fetch(`${WEBUI_API_BASE_URL}/onboarding/structured`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				provider_id: providerId,
				model_id: modelId,
				system,
				user,
				max_tokens: options.maxTokens ?? 4_000,
				timeout_seconds: timeoutSeconds
			}),
			signal: AbortSignal.timeout((timeoutSeconds + 10) * 1_000)
		});
	} catch (error) {
		if (error instanceof DOMException && error.name === 'TimeoutError') {
			throw new Error("Le modèle IA n'a pas répondu dans le temps prévu.");
		}
		throw error;
	}
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

const SITE_SYSTEM = `Tu construis une fiche d'identité commerciale universelle à partir du site
public d'une entreprise. Ce n'est ni un inventaire du site, ni une analyse stratégique.
Réponds uniquement en JSON valide :
{"companyName":"...","facts":[{"id":"site-...","section":"...","label":"...","value":"...",
"sourceUrl":"URL exacte parmi les pages autorisées","confidence":0.0}]}

Sections autorisées :
- Identité et modèle économique
- Offres et positionnement
- Clients et ICP
- Réputation et signaux

Retourne au maximum 10 faits courts, uniquement sur ces sept besoins :
1. identité : métier, secteur, zone géographique et B2B/B2C/mixte ;
2. offre : offres principales, mode de vente, prix publics et offre mise en avant ;
3. ICP supposé : types de clients, taille/secteur/profil et cas clients visibles ;
4. problème résolu : douleur ou besoin client explicitement mentionné ;
5. promesse et différenciation : résultat promis et raisons revendiquées de choisir l'entreprise ;
6. preuves : chiffres, témoignages, références ou certifications réellement visibles ;
7. inconnues : ambiguïtés, contradictions entre pages et informations commerciales essentielles absentes.

Ignore absolument les coordonnées, téléphones, listes exhaustives de catégories ou produits,
nombres de références, variantes, accessoires, menus de navigation, articles de blog individuels
et détails sans effet sur la compréhension commerciale. Résume une gamme en un seul fait utile.
Une idée par fait. Ne transforme jamais une hypothèse en certitude. N'invente ni chiffre, ni
client, ni revenu, ni concurrent. Le statut et la date seront ajoutés par le produit.`;

export const synthesizeSiteFacts = async (
	token: string,
	providerId: string,
	modelId: string,
	crawl: CrawlResult
): Promise<{ companyName: string; facts: EvidenceFact[]; degraded: boolean }> => {
	const pages = crawl.pages?.length ? crawl.pages : [crawl.url];
	let payload: any;
	try {
		payload = await callStructuredModel(
			token,
			providerId,
			modelId,
			SITE_SYSTEM,
			`Pages autorisées :\n${pages.map((page) => `- ${page}`).join('\n')}\n\nContenu :\n${crawl.markdown.slice(0, 14000)}`,
			{ maxTokens: 1_800, timeoutSeconds: 75 }
		);
	} catch {
		const hostname = new URL(crawl.url).hostname.replace(/^www\./, '').split('.')[0];
		const heading =
			crawl.markdown
				.split('\n')
				.find((line) => /^#\s+\S/.test(line))
				?.replace(/^#\s+/, '')
				.trim() ?? '';
		const companyName =
			heading && heading.length <= 80
				? heading
				: hostname
						.split(/[-_]/)
						.filter(Boolean)
						.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
						.join(' ');
		const observedAt = new Date().toISOString().slice(0, 10);
		const lines = crawl.markdown
			.split('\n')
			.map((line) =>
				line
					.replace(/!\[[^\]]*\]\([^)]*\)/g, '')
					.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
					.replace(/^#{1,6}\s+/, '')
					.replace(/[*_`>|]/g, '')
					.replace(/\s+/g, ' ')
					.trim()
			)
			.filter((line) => line.length >= 35 && line.length <= 280);
		const used = new Set<string>();
		const fallbackFacts: EvidenceFact[] = [];
		const addExactFact = (section: string, label: string, pattern: RegExp) => {
			const value = lines.find((line) => !used.has(line) && pattern.test(line));
			if (!value) return;
			used.add(value);
			fallbackFacts.push({
				id: `site-secours-${safeId(label)}`,
				section,
				label,
				value,
				sourceType: 'site',
				sourceUrl: crawl.url,
				observedAt,
				status: 'a_confirmer',
				confidence: 0.55
			});
		};
		addExactFact(
			'Identité et modèle économique',
			'Activité visible sur le site',
			/\b(service|solution|plateforme|spécialis|entreprise|activité)\b/i
		);
		addExactFact(
			'Offres et positionnement',
			'Offre visible sur le site',
			/\b(offre|produit|service|livraison|abonnement|tarif|prix)\b/i
		);
		addExactFact(
			'Clients et ICP',
			'Clientèle évoquée sur le site',
			/\b(client|entreprise|professionnel|particulier|équipe|famille|restaurant)\b/i
		);
		addExactFact(
			'Offres et positionnement',
			'Promesse visible sur le site',
			/\b(permet|simplifi|rédui|amélior|gagner|sans déchet|avantage)\b/i
		);
		return { companyName, facts: fallbackFacts, degraded: true };
	}
	const allowed = new Set(pages);
	const onboardingNoise =
		/\b(téléphone|adresse|contact|accessoires?|exemples? de|segments?|catégorie .*produits?|article de blog)\b/i;
	const facts = normalizeFacts(Array.isArray(payload?.facts) ? payload.facts : [], 'site')
		.filter((fact) => !onboardingNoise.test(`${fact.label} ${fact.value}`))
		.slice(0, 10)
		.map((fact, index) => ({
			...fact,
			id: fact.id.startsWith('site-') ? fact.id : `site-${safeId(fact.label)}-${index + 1}`,
			sourceType: 'site' as const,
			sourceUrl: allowed.has(fact.sourceUrl ?? '') ? fact.sourceUrl : crawl.url,
			status: 'a_confirmer' as const
		}));
	return { companyName: String(payload?.companyName ?? '').trim(), facts, degraded: false };
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
		body: JSON.stringify({ provider: webProvider, queries }),
		signal: AbortSignal.timeout(30_000)
	});
	if (!response.ok)
		throw new Error(String(await responseError(response, 'Recherche Web indisponible.')));
	const companyDomain = new URL(context.siteUrl).hostname.replace(/^www\./, '');
	return serializeSearchItems(await response.json())
		.filter((item) => {
			try {
				const domain = new URL(item.link).hostname.replace(/^www\./, '');
				return domain !== companyDomain && !domain.endsWith(`.${companyDomain}`);
			} catch {
				return false;
			}
		})
		.slice(0, 12);
};

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
	// EXA fournit déjà le titre, l'extrait et l'URL de preuve. Une seconde requête LLM
	// ajoutait plusieurs minutes et pouvait laisser le navigateur dans un état d'attente
	// après la réponse. L'onboarding transforme donc ces résultats localement ; le Big Crawl
	// pourra enrichir et recouper ces signaux plus tard.
	void token;
	void providerId;
	void modelId;
	void context.siteUrl;
	const compact = (value: string, limit: number) => value.trim().slice(0, limit);
	const goalFor = (kind: ExternalBusinessSignal['kind']) => {
		const preferredOutcomes =
			kind === 'besoin_client'
				? ['clients', 'revenus']
				: kind === 'risque'
					? ['risques', 'qualite']
					: kind === 'mouvement_concurrent'
						? ['revenus', 'risques']
						: ['revenus', 'connaissance', 'risques'];
		return (
			context.goals.find((goal) => preferredOutcomes.includes(goal.outcomeId)) ??
			context.goals[0]
		);
	};
	// Un résultat Web est du BRUIT (pas une conclusion sur l'entreprise) quand son titre est une
	// page d'agrégateur de news ou un flux de plusieurs articles datés — ex. « … Business Ambition
	// News Ticker - [16 juillet 2026] … - [12 juillet 2026] … ». On l'écarte avant d'en faire une carte.
	const isNoisyTitle = (raw: string) => {
		const t = (raw || '').toLowerCase();
		if (/news\s?ticker/.test(t)) return true;
		if ((raw.match(/\[\s*\d/g) || []).length >= 2) return true;
		return false;
	};
	// Nettoie la queue d'agrégateur d'un titre qui passe : « Titre - [16 juillet 2026] … » ou « Titre | Site ».
	const cleanTitle = (raw: string) => {
		let t = (raw || '').split(/\s[-|–]\s*\[/)[0];
		t = t.split(/\s[|–]\s/)[0];
		return t.trim();
	};
	// « Impact attendu » : distinct de « Pourquoi cela compte » (whyItMatters), jamais le même texte.
	const impactFor = (kind: ExternalBusinessSignal['kind']) =>
		kind === 'besoin_client'
			? 'Ajuster le discours ou traiter un irritant client avant qu’il ne coûte.'
			: kind === 'mouvement_concurrent'
				? 'Réévaluer une offre ou une priorité commerciale face à ce concurrent.'
				: kind === 'risque'
					? 'Vérifier puis décider s’il faut une action de prévention.'
					: 'Décider si cette évolution ouvre une opportunité à saisir.';
	const normalized: EvidenceFact[] = items
		.filter((item) => !isNoisyTitle(item.title))
		.slice(0, 5)
		.map((item, index) => {
			const text = `${item.title} ${item.snippet}`.toLowerCase();
			const kind: ExternalBusinessSignal['kind'] =
				/avis|client|trustpilot|satisfaction|critique|témoignage/.test(text)
					? 'besoin_client'
					: /concurrent|alternative|comparatif|rachat|acquisition/.test(text)
						? 'mouvement_concurrent'
						: /risque|baisse|plainte|litige|difficulté|menace/.test(text)
							? 'risque'
							: /lancement|partenariat|recrutement|déploiement|expansion|levée/.test(text)
								? 'opportunite'
								: 'signal_marche';
			const goal = goalFor(kind);
			const section =
				kind === 'besoin_client'
					? 'Réputation et signaux'
					: kind === 'mouvement_concurrent' || kind === 'signal_marche'
						? 'Concurrence et marché'
						: 'Réputation et signaux';
			const whyItMatters =
				kind === 'besoin_client'
					? 'Ce signal extérieur peut modifier la confiance, la fidélisation ou le discours client.'
					: kind === 'mouvement_concurrent'
						? 'Ce mouvement peut modifier le positionnement ou les priorités commerciales.'
						: kind === 'risque'
							? 'Ce risque mérite une vérification avant toute décision.'
							: 'Ce signal peut révéler une évolution du marché à surveiller.';
			const cleanLabel = cleanTitle(item.title);
			return {
				id: `web-${safeId(item.title)}-${index + 1}`,
				section,
				label: compact(cleanLabel, 120) || `Signal extérieur ${index + 1}`,
				value: compact(item.snippet || cleanLabel, 320),
				sourceType: 'web' as const,
				sourceUrl: item.link,
				sourceTitle: compact(cleanLabel, 160),
				observedAt: String(item.publishedDate ?? '').slice(0, 10) || '',
				status: 'a_confirmer' as const,
				confidence: 0.72,
				businessSignal: goal
					? {
							kind,
							goalId: goal.id,
							whyItMatters,
							impact: impactFor(kind),
							nextAction: 'Vérifier la source puis décider si ce signal mérite une action.'
						}
					: undefined
			};
		});
	if (context.goals.length && !normalized.some((fact) => fact.businessSignal)) {
		throw new Error(
			"Le Web extérieur n'a produit aucun signal exploitable pour vos priorités. Relancez l'analyse."
		);
	}
	return normalized;
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
