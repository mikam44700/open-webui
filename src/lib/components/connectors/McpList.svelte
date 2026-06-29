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

	const i18n = getContext<Writable<i18nType>>('i18n');

	// Vue MCP rangée par catégorie (esprit Intégrations) : le dirigeant voit les connecteurs
	// utiles regroupés (Productivité, Finance, …). Les connecteurs techniques n'apparaissent
	// qu'en « Réglages avancés » (store expertMode), dans une zone « Connecteurs avancés ».
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
		}
	];

	// Catégories visibles par défaut (dirigeant). Ordre = ordre d'affichage.
	const CATEGORIES = [
		{ key: 'productivity', label: 'Productivité & Bureau', emoji: '💼' },
		{ key: 'finance', label: 'Finance', emoji: '💳' },
		{ key: 'creation', label: 'Création & Média', emoji: '🎨' },
		{ key: 'search', label: 'Recherche', emoji: '🔎' }
	];
	// Catégories réservées au mode avancé (zone « Connecteurs avancés »).
	const EXPERT_CATEGORIES = [
		{ key: 'devops', label: 'DevOps & Développement', emoji: '🛠️' },
		{ key: 'database', label: 'Bases de données', emoji: '🗄️' },
		{ key: 'crypto', label: 'Crypto & Blockchain', emoji: '⛓️' },
		{ key: 'tools', label: 'Outils techniques', emoji: '🔧' },
		{ key: 'other', label: 'Autres', emoji: '📦' }
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

	$: installedIds = new Set(connectors.map((c) => c.id));
	// Presets maison non encore installés + catalogue fusionné (registre + moteur).
	$: presetFeatured = PRESET_FEATURED.filter((e) => !installedIds.has(e.name));
	$: allEntries = [...presetFeatured, ...entries];

	// Entrées d'une catégorie ; en mode simple on ne garde que les « visible ».
	const itemsFor = (all: Entry[], catKey: string, includeExpert: boolean): Entry[] =>
		all.filter(
			(e) =>
				(e.category ?? 'other') === catKey &&
				(includeExpert || (e.visibility ?? 'visible') === 'visible')
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

		<!-- Catégories visibles (le dirigeant). En mode avancé, les entrées expert de ces
		     mêmes catégories (ex. Finance → Alpaca) viennent s'y ajouter. -->
		{#each CATEGORIES as cat (cat.key)}
			{@const items = itemsFor(allEntries, cat.key, $expertMode)}
			{#if items.length > 0}
				<section class="mb-7">
					<div class="text-sm font-medium mb-3 flex items-center gap-2">
						<span aria-hidden="true">{cat.emoji}</span>
						<span>{$i18n.t(cat.label)}</span>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
						{#each items as entry (entry.name)}
							<CatalogCard {entry} on:changed={load} />
						{/each}
					</div>
				</section>
			{/if}
		{/each}

		<!-- Zone « Connecteurs avancés » : visible seulement en Réglages avancés. -->
		{#if $expertMode}
			{@const advCount = EXPERT_CATEGORIES.reduce(
				(n, c) => n + itemsFor(allEntries, c.key, true).length,
				0
			)}
			{#if advCount > 0}
				<div class="flex items-center gap-2 mt-2 mb-5">
					<div class="h-px flex-1 bg-gray-100 dark:bg-gray-850"></div>
					<span class="text-xs font-medium text-gray-400 dark:text-gray-500 inline-flex items-center gap-1.5">
						<span aria-hidden="true">⚡</span>{$i18n.t('Connecteurs avancés')}
					</span>
					<div class="h-px flex-1 bg-gray-100 dark:bg-gray-850"></div>
				</div>
				{#each EXPERT_CATEGORIES as cat (cat.key)}
					{@const items = itemsFor(allEntries, cat.key, true)}
					{#if items.length > 0}
						<section class="mb-7">
							<div class="text-sm font-medium mb-3 flex items-center gap-2">
								<span aria-hidden="true">{cat.emoji}</span>
								<span>{$i18n.t(cat.label)}</span>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
								{#each items as entry (entry.name)}
									<CatalogCard {entry} on:changed={load} />
								{/each}
							</div>
						</section>
					{/if}
				{/each}
			{/if}
		{/if}

		<!-- Connecteurs installés -->
		<div class="text-sm font-medium mt-2 mb-3">{$i18n.t('Connecteurs installés')}</div>
		{#if connectors.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
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

<AddConnectorModal
	bind:open={showAddModal}
	on:added={() => {
		showAddModal = false;
		load();
	}}
	on:close={() => (showAddModal = false)}
/>
