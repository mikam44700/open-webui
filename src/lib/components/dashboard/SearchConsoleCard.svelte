<script lang="ts">
	import { getContext, onMount } from 'svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getSearchConsole, type SearchConsoleSummary } from '$lib/apis/google-services';

	const i18n = getContext('i18n');

	// Google connecté ? (dérivé du dashboard) — on n'appelle l'API que si connecté.
	export let googleConnected: boolean | 'unknown' = 'unknown';

	let loading = false;
	let data: SearchConsoleSummary | null = null;
	let failed = false;

	const load = async () => {
		loading = true;
		failed = false;
		try {
			const res = await getSearchConsole(localStorage.token);
			data = res?.search_console ?? null;
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
		<div class="text-sm font-medium">{$i18n.t('Recherche Google (Search Console)')}</div>
		{#if data?.days}
			<span class="text-[11px] text-gray-500">{$i18n.t('28 derniers jours')}</span>
		{/if}
	</div>

	{#if googleConnected !== true}
		<div class="text-xs text-gray-500 py-2">
			{$i18n.t('Connectez Google dans Intégrations pour voir vos requêtes.')}
		</div>
	{:else if loading}
		<div class="flex justify-center py-4"><Spinner className="size-5" /></div>
	{:else if failed}
		<div class="text-xs text-gray-500 py-2">{$i18n.t('Données indisponibles pour l’instant.')}</div>
	{:else if data?.note === 'no_site'}
		<div class="text-xs text-gray-500 py-2">
			{$i18n.t('Aucun site vérifié dans Search Console sur ce compte.')}
		</div>
	{:else if data && data.queries.length > 0}
		{#if data.site}
			<div class="text-xs text-gray-500 truncate">{data.site}</div>
		{/if}
		<ul class="flex flex-col gap-1">
			{#each data.queries as q (q.query)}
				<li class="flex items-center justify-between gap-2 text-xs">
					<span class="truncate">{q.query}</span>
					<span class="flex-none text-gray-500">
						{q.clicks}
						{$i18n.t('clics')} · {q.impressions}
						{$i18n.t('vues')}
					</span>
				</li>
			{/each}
		</ul>
	{:else}
		<div class="text-xs text-gray-500 py-2">{$i18n.t('Aucune requête à afficher.')}</div>
	{/if}
</div>
