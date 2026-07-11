// Recommandations d'un agent (intégrations OAuth + connecteurs MCP + moteurs de recherche web),
// unifiées pour un rendu unique dans la fiche « Voir ses compétences ». Partagé entre la galerie
// « Prêts à l'emploi » (AgentList) et la page Catalogue (AgentCatalogue) — DRY.
import { getIntegrations } from '$lib/apis/integrations';
import { getConnectors } from '$lib/apis/connectors';
import { getToolConnection } from '$lib/apis/capabilities';
import { INTEGRATION_FR } from '$lib/utils/integrationLabels';
import { CONNECTOR_FR } from '$lib/utils/connectorLabels';
import {
	INTEGRATION_LOGO,
	INTEGRATION_LOGO_BG,
	INTEGRATION_LOGO_FULL_BLEED
} from '$lib/utils/integrationLogos';
import { CONNECTOR_LOGO, CONNECTOR_LOGO_FULL_BLEED } from '$lib/utils/connectorLogos';
import { LOGO_BY_SLUG, providerStatus, type Provider } from '$lib/utils/toolConnect';
import type { AgentTemplate } from './templates';

export type Reco = {
	key: string;
	name: string;
	logo: string | undefined;
	bg: string;
	fullBleed: boolean;
	connected: boolean;
	tab: 'integrations' | 'connectors' | 'web-search';
};

export type RecoState = {
	integrationState: Record<string, string>;
	connectorState: Record<string, string>;
	webState: Record<string, string>;
};

// Nom lisible des moteurs de recherche web (3e réservoir).
const WEBSEARCH_NAME: Record<string, string> = {
	exa: 'Exa',
	brave: 'Brave Search',
	firecrawl: 'Firecrawl',
	tavily: 'Tavily',
	duckduckgo: 'DuckDuckGo',
	crawl4ai: 'Crawl4AI'
};
// Un fournisseur web « branchable » compte comme connecté dès qu'il est réellement utilisable.
const WEB_CONNECTED = new Set(['saved', 'key-active', 'active', 'subscription', 'detected', 'local']);

// État vide (fiche utile même sans connexion : le CTA renvoie vers la bonne page).
export const emptyRecoState = (): RecoState => ({
	integrationState: {},
	connectorState: {},
	webState: {}
});

// Charge l'état RÉEL des trois réservoirs. On ne suppose jamais un état ; en cas d'échec d'une
// source, on garde les autres (dégradation honnête). Silencieux : la fiche reste exploitable.
export const loadRecoState = async (token: string): Promise<RecoState> => {
	const state = emptyRecoState();
	try {
		const res = await getIntegrations(token);
		state.integrationState = Object.fromEntries(
			(res?.integrations ?? []).map((i: { id: string; state: string }) => [i.id, i.state])
		);
	} catch {
		// intégrations indisponibles → on continue
	}
	try {
		const res = await getConnectors(token);
		state.connectorState = Object.fromEntries(
			(res?.connectors ?? []).map((c: { id: string; state: string }) => [c.id, c.state])
		);
	} catch {
		// connecteurs indisponibles → on continue
	}
	try {
		const res = await getToolConnection(token, 'web');
		for (const p of ((res as { providers?: Provider[] })?.providers ?? []) as Provider[]) {
			if (p.slug) state.webState[p.slug] = providerStatus(p);
		}
	} catch {
		// recherche web indisponible → on continue
	}
	return state;
};

// Liste unifiée des recommandations d'un agent, prête à afficher (logo + état + onglet cible).
export const buildReco = (tpl: AgentTemplate | null, state: RecoState): Reco[] => {
	if (!tpl) return [];
	const { integrationState, connectorState, webState } = state;
	const items: Reco[] = [];
	for (const id of tpl.recommendedIntegrations ?? []) {
		const meta = INTEGRATION_FR[id];
		if (!meta) continue;
		items.push({
			key: `i-${id}`,
			name: meta.name,
			logo: INTEGRATION_LOGO[id],
			bg: INTEGRATION_LOGO_BG[id] ?? 'bg-white',
			fullBleed: INTEGRATION_LOGO_FULL_BLEED.has(id),
			connected: integrationState[id] === 'connected' || integrationState[id] === 'key_present',
			tab: 'integrations'
		});
	}
	for (const id of tpl.recommendedConnectors ?? []) {
		items.push({
			key: `c-${id}`,
			name: CONNECTOR_FR[id]?.name ?? id,
			logo: CONNECTOR_LOGO[id],
			bg: 'bg-white',
			fullBleed: CONNECTOR_LOGO_FULL_BLEED.has(id),
			connected: connectorState[id] === 'connected',
			tab: 'connectors'
		});
	}
	for (const slug of tpl.recommendedWebSearch ?? []) {
		items.push({
			key: `w-${slug}`,
			name: WEBSEARCH_NAME[slug] ?? slug,
			logo: LOGO_BY_SLUG[slug] ?? CONNECTOR_LOGO[slug],
			bg: 'bg-white',
			fullBleed: false,
			connected: WEB_CONNECTED.has(webState[slug]),
			tab: 'web-search'
		});
	}
	return items;
};
