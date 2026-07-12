import { WEBUI_API_BASE_URL } from '$lib/constants';
import { generateOpenAIChatCompletion } from '$lib/apis/openai';
import {
	parseSynthesis,
	buildSynthesisUserContent,
	SYNTHESIS_SYSTEM_PROMPT,
	EMPTY_CONTEXT,
	type CompanyContext
} from '$lib/onboarding/companySynthesis';

// Client de l'onboarding (spec 019). Deux temps :
//  1. crawlSite → proxy /api/v1/onboarding/crawl → bridge → Crawl4AI (LECTURE déterministe du site) ;
//  2. synthesizeContext → MODÈLE ACTIF (markdown → offre/ton/clientèle/services, jamais inventé).
// La persistance du contexte validé réutilise apis/memory (saveProfile propage aux profils + inbox).

export type CrawlStatus = 'reussi' | 'partiel' | 'echec';

export type CrawlResult = {
	status: CrawlStatus;
	markdown: string;
	chars: number;
	message?: string | null;
	url: string;
	pages?: string[]; // URLs réellement lues (home + pages clés) — crawl multi-pages
};

// Crawle le site du client. Dégradé gracieux : une erreur réseau/HTTP renvoie un `echec` honnête
// (jamais une exception qui casserait le parcours) ; seule une URL invalide remonte le message 400.
export const crawlSite = async (token: string, url: string): Promise<CrawlResult> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/onboarding/crawl`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ url })
		});
		if (res.status === 400) {
			return { status: 'echec', markdown: '', chars: 0, url, message: 'URL invalide.' };
		}
		if (!res.ok) {
			return {
				status: 'echec',
				markdown: '',
				chars: 0,
				url,
				message: 'Le service d’analyse est indisponible.'
			};
		}
		return (await res.json()) as CrawlResult;
	} catch (err) {
		console.error(err);
		return {
			status: 'echec',
			markdown: '',
			chars: 0,
			url,
			message: 'Le site n’a pas pu être lu (erreur réseau).'
		};
	}
};

// Résume le markdown du site en CompanyContext via le modèle actif. Ne lève jamais : un échec de
// synthèse (modèle indisponible, réponse illisible) renvoie un contexte VIDE — le parcours bascule
// alors sur la saisie manuelle / le repli, plutôt que d'inventer.
export const synthesizeContext = async (
	token: string,
	model: string,
	markdown: string
): Promise<CompanyContext> => {
	if (!model || !markdown.trim()) return { ...EMPTY_CONTEXT };
	try {
		const res = await generateOpenAIChatCompletion(token, {
			model,
			stream: false,
			temperature: 0.2,
			messages: [
				{ role: 'system', content: SYNTHESIS_SYSTEM_PROMPT },
				{ role: 'user', content: buildSynthesisUserContent(markdown) }
			]
		});
		const content = res?.choices?.[0]?.message?.content ?? '';
		return parseSynthesis(content);
	} catch (err) {
		console.error(err);
		return { ...EMPTY_CONTEXT };
	}
};
