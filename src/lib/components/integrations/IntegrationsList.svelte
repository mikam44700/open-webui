<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	import { getIntegrations } from '$lib/apis/integrations';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import IntegrationCard from './IntegrationCard.svelte';
	import IntegrationsBrowseModal from './IntegrationsBrowseModal.svelte';

	const i18n = getContext('i18n');

	type Integration = {
		id: string;
		auth_mode: 'account' | 'key' | 'credentials' | 'path' | 'local';
		state: 'not_connected' | 'key_present' | 'connected' | 'error' | 'unavailable';
		secret_state?: 'present' | 'absent' | null;
		subservices?: string[];
		visible?: boolean;
		local_only?: boolean;
		reason?: string | null;
	};

	let loading = true;
	let bridgeDown = false;
	let integrations: Integration[] = [];
	let showBrowse = false;
	let focusedSearch = '';
	const MAIN_IDS = [
		'google-workspace',
		'microsoft-365',
		'notion',
		'airtable',
		'obsidian',
		'calendly'
	];

	// Le client final ne voit que les intégrations visibles (les masquées restent gérées en admin).
	$: visible = integrations.filter((i) => i.visible !== false);
	// La page principale reste volontairement courte. Les réseaux sociaux et les
	// autres applications demeurent disponibles dans « Tout parcourir ».
	$: main = MAIN_IDS.map((id) => visible.find((i) => i.id === id)).filter(
		(i): i is Integration => !!i
	);
	// Déjà connectées (ou clé enregistrée) — mises en avant EN HAUT de page.
	$: connected = main.filter((i) => i.state === 'connected' || i.state === 'key_present');
	$: connectedIds = new Set(connected.map((i) => i.id));
	// « À découvrir » : tout ce qui n'est pas déjà connecté (évite le doublon avec la section du haut).
	$: featured = main.filter((i) => !connectedIds.has(i.id));

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	// Un echec transitoire (stack qui vient de redemarrer, moteur pas encore chaud) se
	// retente UNE fois en silence avant d'alerter — jamais d'erreur rouge au demarrage.
	const load = async (attempt = 0) => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getIntegrations(localStorage.token);
			integrations = res?.integrations ?? [];
			loading = false;
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
				loading = false;
			} else if (attempt < 1) {
				setTimeout(() => load(attempt + 1), 2500);
			} else {
				toast.error($i18n.t('Échec du chargement des intégrations'));
				loading = false;
			}
		}
	};

	onMount(() => {
		focusedSearch = $page.url.searchParams.get('search')?.trim() ?? '';
		if (focusedSearch) showBrowse = true;
		load();
	});
</script>

<div class="w-full max-w-7xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Intégrations est injoignable')}</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else if visible.length > 0}
		<!-- Applications connectées — remontées EN HAUT et mises en avant (si non vide) -->
		{#if connected.length > 0}
			<div class="text-sm font-medium mb-3">{$i18n.t('Applications connectées')}</div>
			<div class="responsive-card-grid">
				{#each connected as integration (integration.id)}
					<IntegrationCard {integration} on:changed={load} />
				{/each}
			</div>
		{/if}

		<!-- À découvrir (ou « Les plus populaires » si rien n'est encore connecté) + catalogue complet -->
		{#if featured.length > 0}
			<div class="flex items-center justify-between mb-3 {connected.length > 0 ? 'mt-8' : ''}">
				<div class="text-sm font-medium">
					{connected.length > 0 ? $i18n.t('À découvrir') : $i18n.t('Les plus populaires')}
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

			<div class="responsive-card-grid">
				{#each featured as integration (integration.id)}
					<IntegrationCard {integration} on:changed={load} />
				{/each}
			</div>
		{/if}
	{:else}
		<div class="text-xs text-gray-500 text-center py-8">
			{$i18n.t('Aucune intégration disponible')}
		</div>
	{/if}
</div>

<IntegrationsBrowseModal
	bind:open={showBrowse}
	integrations={visible}
	initialSearch={focusedSearch}
	on:changed={load}
/>

<style>
	.responsive-card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
		gap: 0.75rem;
	}
</style>
