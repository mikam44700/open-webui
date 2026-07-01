<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { getToolConnection } from '$lib/apis/capabilities';
	import { getConnectors } from '$lib/apis/connectors';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ToolProviderCatalogCard from '$lib/components/integrations/ToolProviderCatalogCard.svelte';
	import WebSearchBrowseModal from '$lib/components/capabilities/WebSearchBrowseModal.svelte';
	import Crawl4aiCard from '$lib/components/connectors/Crawl4aiCard.svelte';
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

	// Vedettes « Les plus populaires » : liste choisie à la main (par slug), dans cet ordre.
	// Tout le reste reste accessible via « Tout parcourir ».
	const FEATURED_SLUGS = ['duckduckgo', 'exa', 'firecrawl', 'brave', 'tavily'];
	$: featured = FEATURED_SLUGS.map((slug) =>
		items.find((it) => it.provider.slug === slug)
	).filter(Boolean) as Item[];
	// Déjà branchés = clé enregistrée ou compte connecté (état réel, jamais inventé).
	$: connected = items.filter((it) =>
		['saved', 'detected'].includes(providerStatus(it.provider))
	);

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const conn = await getConnectors(localStorage.token).catch(() => null);
			connectors = conn?.connectors ?? [];
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
		<!-- Les plus populaires + accès au catalogue complet -->
		<div class="flex items-center justify-between mb-3">
			<div class="text-sm font-medium">{$i18n.t('Les plus populaires')}</div>
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
					<path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
				</svg>
			</button>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
			<!-- Crawl4AI : connecteur MCP « maison » (lecture web approfondie), déplacé ici depuis MCP. -->
			<Crawl4aiCard on:changed={load} />
			<!-- Apify : connecteur MCP « maison » (extraction web / prospection). Géré si branché,
			     sinon proposé à l'installation (clé API requise, payant à l'usage). -->
			{#if apifyConnector}
				<ConnectorCard connector={apifyConnector} on:changed={load} />
			{:else}
				<CatalogCard entry={apifyEntry} on:changed={load} />
			{/if}
			{#each featured as it (it.toolsetName + ':' + it.provider.name)}
				<ToolProviderCatalogCard toolsetName={it.toolsetName} provider={it.provider} on:changed={load} />
			{/each}
		</div>

		<!-- Fournisseurs déjà branchés -->
		<div class="text-sm font-medium mt-7 mb-3">{$i18n.t('Déjà connectés')}</div>
		{#if connected.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				{#each connected as it (it.toolsetName + ':' + it.provider.name)}
					<ToolProviderCatalogCard toolsetName={it.toolsetName} provider={it.provider} on:changed={load} />
				{/each}
			</div>
		{:else}
			<div class="text-xs text-gray-500 py-4">
				{$i18n.t('Aucun fournisseur branché pour l’instant.')}
			</div>
		{/if}
	{/if}
</div>

<WebSearchBrowseModal bind:open={showBrowse} {items} on:changed={load} />
