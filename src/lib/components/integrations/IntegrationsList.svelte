<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getIntegrations } from '$lib/apis/integrations';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import IntegrationCard from './IntegrationCard.svelte';

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

	// Le client final ne voit que les intégrations visibles (les masquées restent gérées en admin).
	$: visible = integrations.filter((i) => i.visible !== false);

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

<div class="w-full max-w-5xl mx-auto px-3 py-3">

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
		<div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
			{#each visible as integration (integration.id)}
				<IntegrationCard {integration} on:changed={load} />
			{/each}
		</div>
	{:else}
		<div class="text-xs text-gray-500 text-center py-8">{$i18n.t('Aucune intégration disponible')}</div>
	{/if}
</div>
