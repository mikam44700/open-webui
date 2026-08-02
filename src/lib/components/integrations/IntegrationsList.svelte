<script lang="ts">
	import { getContext, onMount } from 'svelte';
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

	// Les 6 intégrations essentielles visibles sur la page, dans l'ordre produit décidé.
	// Le catalogue « Tout parcourir » continue de recevoir toutes les intégrations visibles.
	const HOME_INTEGRATION_IDS = [
		'google-workspace',
		'microsoft-365',
		'obsidian',
		'notion',
		'airtable',
		'linkedin'
	];

	// Le client final ne voit que les intégrations visibles (les masquées restent gérées en admin).
	$: visible = integrations.filter((i) => i.visible !== false);
	$: home = HOME_INTEGRATION_IDS.map((id) => visible.find((i) => i.id === id)).filter(
		(i): i is Integration => i !== undefined
	);

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getIntegrations(localStorage.token);
			integrations = res?.integrations ?? [];
		} catch (err) {
			if (isBridgeDown(err)) bridgeDown = true;
			else toast.error($i18n.t('Échec du chargement des intégrations'));
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
			<div class="text-sm font-medium">{$i18n.t('Le service Intégrations est injoignable')}</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else if visible.length > 0}
		<!-- Sélection fixe de 6 cartes + catalogue complet. Leur ordre reste identique même connectées. -->
		{#if home.length > 0}
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
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
						/>
					</svg>
				</button>
			</div>

			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				{#each home as integration (integration.id)}
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

<IntegrationsBrowseModal bind:open={showBrowse} integrations={visible} on:changed={load} />
