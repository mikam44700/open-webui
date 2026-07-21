<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { getCrawl4aiStatus, getToolConnection } from '$lib/apis/capabilities';
	import { getConnectors } from '$lib/apis/connectors';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ToolProviderCatalogCard from '$lib/components/integrations/ToolProviderCatalogCard.svelte';
	import WebSearchBrowseModal from '$lib/components/capabilities/WebSearchBrowseModal.svelte';
	import Crawl4aiCard from '$lib/components/connectors/Crawl4aiCard.svelte';
	import PublicSourcesCard from '$lib/components/capabilities/PublicSourcesCard.svelte';
	import Last30DaysCard from '$lib/components/capabilities/Last30DaysCard.svelte';
	import CatalogCard from '$lib/components/connectors/CatalogCard.svelte';
	import ConnectorCard from '$lib/components/connectors/ConnectorCard.svelte';
	import { type Provider, providerStatus } from '$lib/utils/toolConnect';

	// Apify = connecteur MCP « maison » (extraction web / prospection), présenté ici comme
	// Crawl4AI : install en 1 clic avec clé API (payant à l'usage), géré une fois branché.
	const APIFY_ENTRY = {
		name: 'apify',
		transport: 'http' as const,
		auth_type: 'key' as const,
		installed: false,
		category: 'search',
		visibility: 'visible' as const,
		installable: true,
		preset: { transport: 'http' as const, url: 'https://mcp.apify.com', auth_type: 'key' as const }
	};

	const i18n = getContext<Writable<i18nType>>('i18n');

	// Toolsets natifs Hermes agrégés dans cette page (recherche web + navigateur + X).
	export let names: string[] = ['web', 'browser', 'x_search'];

	type Item = { toolsetName: string; provider: Provider };

	let loading = true;
	let bridgeDown = false;
	let items: Item[] = [];
	let connectors: any[] = [];
	let showBrowse = false;

	// Connecteur Apify déjà branché ? (état réel côté bridge, jamais inventé).
	$: apifyConnector = connectors.find((c) => c.id === 'apify');
	$: apifyEntry = { ...APIFY_ENTRY, installed: !!apifyConnector };

	// Actifs = tout ce qui marche déjà, remonté EN HAUT (demande Michael 2026-07-18) :
	// service sans clé actif (DuckDuckGo, navigateur local), compte connecté, clé
	// enregistrée ou clé active. État réel côté bridge, jamais inventé.
	const ACTIVE_STATES = ['saved', 'detected', 'active', 'key-active'];
	$: connected = items.filter((it) => ACTIVE_STATES.includes(providerStatus(it.provider)));
	// Crawl4AI actif ? (sa carte dédiée rejoint alors la section « Actifs »)
	let crawl4aiActive = false;
	$: hasActive = true;
	$: connectedKeys = new Set(connected.map((it) => it.toolsetName + ':' + it.provider.name));
	// Vedettes « Les plus populaires » : liste choisie à la main (par slug), dans cet ordre.
	// On exclut ceux déjà branchés (remontés en haut) pour éviter le doublon.
	const FEATURED_SLUGS = ['duckduckgo', 'exa', 'firecrawl', 'brave', 'tavily'];
	$: featured = (
		FEATURED_SLUGS.map((slug) => items.find((it) => it.provider.slug === slug)).filter(
			Boolean
		) as Item[]
	).filter((it) => !connectedKeys.has(it.toolsetName + ':' + it.provider.name));

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const conn = await getConnectors(localStorage.token).catch(() => null);
			connectors = conn?.connectors ?? [];
			const c4 = await getCrawl4aiStatus(localStorage.token).catch(() => null);
			crawl4aiActive = !!c4?.active;
			const seen = new Set<string>();
			const out: Item[] = [];
			// Chaque toolset chargé en parallèle ; on aplatit et on dédoublonne par nom affiché
			// (ex. « Abonnement Nous » présent dans plusieurs services → une seule carte).
			const results = await Promise.all(
				names.map(async (toolsetName) => {
					try {
						const conn = await getToolConnection(localStorage.token, toolsetName);
						return { toolsetName, providers: (conn?.providers ?? []) as Provider[] };
					} catch {
						return { toolsetName, providers: [] as Provider[] };
					}
				})
			);
			for (const { toolsetName, providers } of results) {
				for (const provider of providers) {
					if (seen.has(provider.name)) continue;
					seen.add(provider.name);
					out.push({ toolsetName, provider });
				}
			}
			items = out;
		} catch {
			bridgeDown = true;
		} finally {
			loading = false;
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-7xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<div class="text-sm text-gray-500 text-center py-16">
			{$i18n.t('Service indisponible pour le moment. Réessaie dans un instant.')}
		</div>
	{:else if items.length === 0}
		<div class="text-sm text-gray-500 text-center py-16">
			{$i18n.t('Aucun fournisseur disponible.')}
		</div>
	{:else}
		<!-- Actifs — tout ce qui marche déjà, remonté EN HAUT (Crawl4AI en premier) -->
		{#if hasActive}
			<div class="text-sm font-medium mb-3">{$i18n.t('Actifs')}</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				<PublicSourcesCard />
				<Last30DaysCard />
				{#if crawl4aiActive}
					<Crawl4aiCard showMcpBadge on:changed={load} />
				{/if}
				{#if apifyConnector}
					<ConnectorCard connector={apifyConnector} showMcpBadge on:changed={load} />
				{/if}
				{#each connected as it (it.toolsetName + ':' + it.provider.name)}
					<ToolProviderCatalogCard
						toolsetName={it.toolsetName}
						provider={it.provider}
						on:changed={load}
					/>
				{/each}
			</div>
		{/if}

		<!-- À découvrir (ou « Les plus populaires » si rien n'est actif) + catalogue complet -->
		<div class="flex items-center justify-between mb-3 {hasActive ? 'mt-8' : ''}">
			<div class="text-sm font-medium">
				{hasActive ? $i18n.t('À découvrir') : $i18n.t('Les plus populaires')}
			</div>
			<button
				type="button"
				class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white transition inline-flex items-center gap-1"
				on:click={() => (showBrowse = true)}
			>
				{$i18n.t('Tout parcourir')}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="size-4"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
					/>
				</svg>
			</button>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
			<!-- Crawl4AI : carte dédiée (lecture web approfondie). Si actif, elle est déjà
			     affichée dans « Actifs » ci-dessus — pas de doublon ici. -->
			{#if !crawl4aiActive}
				<Crawl4aiCard showMcpBadge on:changed={load} />
			{/if}
			<!-- Apify : proposé à l'installation ici ; une fois branché il vit dans « Actifs ». -->
			{#if !apifyConnector}
				<CatalogCard entry={apifyEntry} showMcpBadge on:changed={load} />
			{/if}
			{#each featured as it (it.toolsetName + ':' + it.provider.name)}
				<ToolProviderCatalogCard
					toolsetName={it.toolsetName}
					provider={it.provider}
					on:changed={load}
				/>
			{/each}
		</div>
	{/if}
</div>

<WebSearchBrowseModal bind:open={showBrowse} {items} on:changed={load} />
