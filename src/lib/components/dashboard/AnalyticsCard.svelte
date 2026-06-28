<script lang="ts">
	import { getContext, onMount } from 'svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getAnalytics, type AnalyticsSummary } from '$lib/apis/google-services';

	const i18n = getContext('i18n');

	// Google connecté ? (dérivé du dashboard) — on n'appelle l'API que si connecté.
	export let googleConnected: boolean | 'unknown' = 'unknown';

	let loading = false;
	let data: AnalyticsSummary | null = null;
	let failed = false;

	const load = async () => {
		loading = true;
		failed = false;
		try {
			const res = await getAnalytics(localStorage.token);
			data = res?.analytics ?? null;
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		if (googleConnected === true) load();
	});
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850">
	<div class="flex items-center justify-between">
		<div class="text-sm font-medium">{$i18n.t('Audience du site (Analytics)')}</div>
		{#if data?.days}
			<span class="text-[11px] text-gray-500">{$i18n.t('7 derniers jours')}</span>
		{/if}
	</div>

	{#if googleConnected !== true}
		<div class="text-xs text-gray-500 py-2">
			{$i18n.t('Connectez Google dans Intégrations pour voir vos statistiques.')}
		</div>
	{:else if loading}
		<div class="flex justify-center py-4"><Spinner className="size-5" /></div>
	{:else if failed}
		<div class="text-xs text-gray-500 py-2">{$i18n.t('Statistiques indisponibles pour l’instant.')}</div>
	{:else if data?.note === 'no_property'}
		<div class="text-xs text-gray-500 py-2">
			{$i18n.t('Aucune propriété Google Analytics trouvée sur ce compte.')}
		</div>
	{:else if data && data.metrics.length > 0}
		{#if data.property}
			<div class="text-xs text-gray-500 truncate">{data.property}</div>
		{/if}
		<div class="grid grid-cols-3 gap-2">
			{#each data.metrics as m (m.label)}
				<div class="flex flex-col items-center p-2 rounded-xl bg-gray-50 dark:bg-gray-850">
					<div class="text-base font-semibold">{m.value}</div>
					<div class="text-[10px] text-gray-500 text-center leading-tight">{$i18n.t(m.label)}</div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="text-xs text-gray-500 py-2">{$i18n.t('Aucune donnée à afficher.')}</div>
	{/if}
</div>
