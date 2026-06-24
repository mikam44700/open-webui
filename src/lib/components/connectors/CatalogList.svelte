<script lang="ts">
	import { getContext, onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getCatalog } from '$lib/apis/connectors';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CatalogCard from './CatalogCard.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	type Entry = {
		name: string;
		description?: string;
		transport: 'stdio' | 'http' | 'sse';
		auth_type: 'none' | 'key' | 'oauth';
		installed: boolean;
		source_url?: string | null;
	};

	let loading = true;
	let bridgeDown = false;
	let entries: Entry[] = [];

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	export const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getCatalog(localStorage.token);
			entries = res?.entries ?? [];
		} catch (err) {
			if (isBridgeDown(err)) bridgeDown = true;
			else toast.error($i18n.t('Échec du chargement du catalogue'));
		} finally {
			loading = false;
		}
	};

	onMount(load);
</script>

{#if loading}
	<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
{:else if bridgeDown}
	<div class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl">
		<div class="text-sm font-medium">{$i18n.t('Le service Connecteurs est injoignable')}</div>
		<button
			class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
			on:click={load}
		>
			{$i18n.t('Réessayer')}
		</button>
	</div>
{:else if entries.length > 0}
	<div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
		{#each entries as entry (entry.name)}
			<CatalogCard
				{entry}
				on:changed={() => {
					load();
					dispatch('changed');
				}}
			/>
		{/each}
	</div>
{:else}
	<div class="text-xs text-gray-500 text-center py-8">{$i18n.t('Catalogue vide')}</div>
{/if}
