<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { getCatalog, getConnectors } from '$lib/apis/connectors';
	import { expertMode } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CatalogCard from './CatalogCard.svelte';
	import ConnectorCard from './ConnectorCard.svelte';
	import AddConnectorModal from './AddConnectorModal.svelte';
	import McpBrowseModal from './McpBrowseModal.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	// Page MCP « esprit Intégrations » : seulement les vedettes essentielles ici ; le catalogue
	// complet rangé par catégorie vit dans la modale « Tout parcourir » (McpBrowseModal).
	type Entry = {
		name: string;
		description?: string;
		transport: 'stdio' | 'http' | 'sse';
		auth_type: 'none' | 'key' | 'oauth';
		installed: boolean;
		source_url?: string | null;
		label?: string;
		icon_url?: string | null;
		category?: string;
		visibility?: 'visible' | 'expert';
		installable?: boolean;
		url?: string | null;
		install_method?: string;
		config_fields?: {
			key: string;
			label?: string;
			type?: string;
			secret?: boolean;
			required?: boolean;
		}[];
		// Connecteur hors catalogue Hermes (ajouté en custom http/OAuth au clic).
		preset?: { transport: 'http' | 'sse'; url: string; auth_type: 'none' | 'key' | 'oauth' };
	};

	// Vedettes « maison » absentes du catalogue Hermes mais branchables via leur serveur
	// MCP officiel (http + connexion par compte). Ex. HubSpot → mcp.hubspot.com.
	const PRESET_FEATURED: Entry[] = [
		{
			name: 'hubspot',
			transport: 'http',
			auth_type: 'oauth',
			installed: false,
			category: 'productivity',
			visibility: 'visible',
			installable: true,
			preset: { transport: 'http', url: 'https://mcp.hubspot.com/', auth_type: 'oauth' }
		},
		{
			// Serveur MCP officiel de data.gouv.fr (déjà hébergé par l'État, transport
			// « streamable HTTP » → déclaré en `http` côté bridge, Hermes le résout au runtime).
			// Read-only, aucune clé → install directe en 1 clic (auth_type: none).
			name: 'data-gouv-fr',
			transport: 'http',
			auth_type: 'none',
			installed: false,
			category: 'search',
			visibility: 'visible',
			installable: true,
			preset: { transport: 'http', url: 'https://mcp.data.gouv.fr/mcp', auth_type: 'none' }
		}
	];

	// Vedettes essentielles affichées sur la page (les autres dans « Tout parcourir »).
	const FEATURED = [
		'gmail',
		'google-calendar',
		'notion',
		'slack',
		'stripe',
		'hubspot',
		'data-gouv-fr'
	];

	type Connector = {
		id: string;
		transport: 'stdio' | 'http' | 'sse';
		auth_type: 'none' | 'key' | 'oauth';
		enabled: boolean;
		state: 'connected' | 'disconnected' | 'error' | 'disabled' | 'incomplete' | 'auth_required';
		endpoint?: string;
		secret_state?: 'present' | 'absent';
		source?: string | null;
	};

	let loading = true;
	let bridgeDown = false;
	let entries: Entry[] = [];
	let connectors: Connector[] = [];
	let showAddModal = false;
	let showBrowse = false;
	const ADVANCED_MANAGED = new Set([
		'bodacc',
		'data-gouv-fr',
		'recherche-entreprises',
		'officecli'
	]);

	$: installedIds = new Set(connectors.map((c) => c.id));
	$: displayedConnectors = connectors.filter((c) => $expertMode || !ADVANCED_MANAGED.has(c.id));
	// Presets maison non encore installés + catalogue fusionné (registre + moteur).
	$: presetFeatured = PRESET_FEATURED.filter((e) => !installedIds.has(e.name));
	$: allEntries = [...presetFeatured, ...entries];

	// Vedettes : les essentiels (dans l'ordre défini), s'ils existent au catalogue.
	$: featured = FEATURED.map((id) => allEntries.find((e) => e.name === id)).filter(
		(e): e is Entry => !!e && !installedIds.has(e.name)
	);

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const [cat, conn] = await Promise.all([
				getCatalog(localStorage.token),
				getConnectors(localStorage.token)
			]);
			// Crawl4AI a sa carte dédiée dans « Recherche & web ». Les autres
			// connecteurs gérés sont chargés, puis réservés au mode avancé ci-dessus.
			const hiddenManaged = new Set(['crawl4ai', 'sources-publiques']);
			entries = (cat?.entries ?? []).filter((e) => !hiddenManaged.has(e.name));
			connectors = (conn?.connectors ?? []).filter((c) => !hiddenManaged.has(c.id));
		} catch (err) {
			if (isBridgeDown(err)) bridgeDown = true;
			else toast.error($i18n.t('Échec du chargement des connecteurs'));
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
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Connecteurs est injoignable')}</div>
			<div class="text-xs text-gray-500 max-w-md">
				{$i18n.t('Le moteur ne répond pas. Vérifie qu’il tourne, puis réessaie.')}
			</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else}
		<!-- Ajout d'un connecteur sur mesure : action mise en avant sous la bannière. -->
		<!-- Connecteurs installés — remontés EN HAUT et mis en avant (si non vide) -->
		{#if displayedConnectors.length > 0}
			<div class="text-sm font-medium mb-3">{$i18n.t('Connecteurs installés')}</div>
			<div class="responsive-card-grid mb-7">
				{#each displayedConnectors as connector (connector.id)}
					<ConnectorCard {connector} on:changed={load} />
				{/each}
			</div>
		{/if}

		<button
			type="button"
			class="w-full mb-7 flex items-center justify-center gap-2 rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 px-4 py-4 text-sm font-medium text-gray-600 dark:text-gray-300 hover:border-gray-400 hover:bg-gray-50 dark:hover:border-gray-600 dark:hover:bg-white/[0.03] transition"
			on:click={() => (showAddModal = true)}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2"
				stroke="currentColor"
				class="size-4"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
			</svg>
			{$i18n.t('Ajouter un connecteur personnalisé')}
		</button>

		<!-- Les plus populaires + accès au catalogue complet (recherche + catégories). -->
		<div class="flex items-center justify-between mb-3">
			<div class="text-sm font-medium">
				{connectors.length > 0 ? $i18n.t('À découvrir') : $i18n.t('Les plus populaires')}
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

		<!-- Crawl4AI a été déplacé vers l'onglet « Recherche & web » (c'est de la lecture web). -->
		<div class="responsive-card-grid">
			{#each featured as entry (entry.name)}
				<CatalogCard {entry} on:changed={load} />
			{/each}
		</div>
		{#if featured.length === 0}
			<div class="text-xs text-gray-500 py-4">
				{$i18n.t('Ouvre « Tout parcourir » pour voir tous les connecteurs.')}
			</div>
		{/if}
	{/if}
</div>

<AddConnectorModal
	bind:open={showAddModal}
	on:added={() => {
		showAddModal = false;
		load();
	}}
	on:close={() => (showAddModal = false)}
/>

<!-- Catalogue complet recherchable (tous les connecteurs, visibles + avancés). -->
<McpBrowseModal bind:open={showBrowse} entries={allEntries} on:changed={load} />

<style>
	.responsive-card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
		gap: 0.75rem;
	}
</style>
