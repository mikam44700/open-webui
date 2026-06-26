<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getConnectors } from '$lib/apis/connectors';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConnectorCard from './ConnectorCard.svelte';

	const i18n = getContext('i18n');

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
	let connectors: Connector[] = [];
	let search = '';

	$: filtered = search.trim()
		? connectors.filter((c) => c.id.toLowerCase().includes(search.toLowerCase()))
		: connectors;

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getConnectors(localStorage.token);
			connectors = res?.connectors ?? [];
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Échec du chargement des connecteurs'));
			}
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
		<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">
			{$i18n.t('Connecteurs avancés de ton assistant')}
		</div>

		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Rechercher un connecteur')}
			bind:value={search}
		/>

		{#if filtered.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
				{#each filtered as connector (connector.id)}
					<ConnectorCard {connector} on:changed={load} />
				{/each}
			</div>
		{:else}
			<div
				class="flex flex-col items-center justify-center text-center py-16 gap-2 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
			>
				<div class="text-sm font-medium">{$i18n.t('Aucun connecteur pour l’instant')}</div>
				<div class="text-xs text-gray-500 max-w-md">
					{$i18n.t('Installe un connecteur depuis le catalogue pour brancher un outil à ton cerveau.')}
				</div>
			</div>
		{/if}
	{/if}
</div>
