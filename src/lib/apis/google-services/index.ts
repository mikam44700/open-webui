import { WEBUI_API_BASE_URL } from '$lib/constants';

// Client API des services Google additionnels (Slides / Analytics / Search Console).
// Appelle le router admin /api/v1/google, qui proxifie vers le Providers Bridge →
// google_direct (appels Google directs, moteur Hermes intact). Source de vérité = Google.

const call = async (token: string, method: string, path: string, body?: unknown) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/google${path}`, {
		method,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail ?? err;
			return null;
		});

	if (error) throw error;
	return res;
};

export type CreatedPresentation = {
	status: string;
	id: string;
	title: string;
	url: string;
	slides: number;
};

// Crée une présentation Google Slides. `slides` = plan optionnel (une diapo par ligne).
export const createPresentation = (
	token: string,
	title: string,
	slides: string[] = []
): Promise<{ presentation: CreatedPresentation }> =>
	call(token, 'POST', '/slides', { title, slides });

export type AnalyticsSummary = {
	connected: boolean;
	property: string;
	days?: number;
	metrics: { label: string; value: string }[];
	note?: string;
};

// Résumé Google Analytics (GA4) en lecture seule.
export const getAnalytics = (token: string): Promise<{ analytics: AnalyticsSummary }> =>
	call(token, 'GET', '/analytics');

export type SearchConsoleSummary = {
	connected: boolean;
	site: string;
	days?: number;
	queries: { query: string; clicks: number; impressions: number }[];
	note?: string;
};

// Top requêtes Google Search Console (lecture seule).
export const getSearchConsole = (token: string): Promise<{ search_console: SearchConsoleSummary }> =>
	call(token, 'GET', '/search-console');
