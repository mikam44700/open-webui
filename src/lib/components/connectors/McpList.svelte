<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getCatalog, getConnectors } from '$lib/apis/connectors';
	import { CONNECTOR_FR } from '$lib/utils/connectorLabels';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CatalogCard from './CatalogCard.svelte';
	import ConnectorCard from './ConnectorCard.svelte';
	import McpBrowseModal from './McpBrowseModal.svelte';
	import AddConnectorModal from './AddConnectorModal.svelte';

	const i18n = getContext('i18n');

	// Vue MCP « esprit Intégrations » : vedettes du catalogue + « Tout parcourir » (modale)
	// + section des connecteurs réellement installés (statut honnête via getConnectors).
	type Entry = {
		name: string;
		description?: string;
		transport: 'stdio' | 'http' | 'sse';
		auth_type: 'none' | 'key' | 'oauth';
		installed: boolean;
		source_url?: string | null;
	};
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
	let showBrowse = false;
	let showAddModal = false;

	// Vedettes : connecteurs marqués « populaires » dans les libellés FR ;
	// repli sur les 4 premiers non installés (à découvrir) sinon les 4 premiers.
	$: notInstalled = entries.filter((e) => !e.installed);
	$: popular = entries.filter((e) => CONNECTOR_FR[e.name]?.popular);
	$: featured =
		popular.length > 0 ? popular.slice(0, 4) : (notInstalled.length > 0 ? notInstalled : entries).slice(0, 4);

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
			entries = cat?.entries ?? [];
			connectors = conn?.connectors ?? [];
		} catch (err) {
			if (isBridgeDown(err)) bridgeDown = true;
			else toast.error($i18n.t('Échec du chargement des connecteurs'));
		} finally {
			loading = false;
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-5xl mx-auto px-3 py-3">
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
		<!-- Ajout d'un connecteur sur mesure : action mise en avant sous la bannière,
		     pour que le client sache qu'il peut brancher son propre MCP. -->
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

		{#if featured.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				{#each featured as entry (entry.name)}
					<CatalogCard {entry} on:changed={load} />
				{/each}
			</div>
		{:else}
			<div class="text-xs text-gray-500 py-4">{$i18n.t('Catalogue vide')}</div>
		{/if}

		<!-- Connecteurs installés -->
		<div class="text-sm font-medium mt-7 mb-3">{$i18n.t('Connecteurs installés')}</div>
		{#if connectors.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				{#each connectors as connector (connector.id)}
					<ConnectorCard {connector} on:changed={load} />
				{/each}
			</div>
		{:else}
			<div class="text-xs text-gray-500 py-4">
				{$i18n.t('Aucun connecteur installé pour l’instant.')}
			</div>
		{/if}
	{/if}
</div>

<McpBrowseModal bind:open={showBrowse} {entries} on:changed={load} />

<AddConnectorModal
	bind:open={showAddModal}
	on:added={() => {
		showAddModal = false;
		load();
	}}
	on:close={() => (showAddModal = false)}
/>
