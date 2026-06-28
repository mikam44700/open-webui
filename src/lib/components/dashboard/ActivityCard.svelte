<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let loading = false;
	export let unavailable = false;
	/** Compteurs prêts à afficher : libellé dirigeant + nombre. */
	export let counts: { label: string; n: number }[] = [];
	/** Tâches récentes : titre + libellé de statut dirigeant + en attente de validation. */
	export let recent: { title: string; statusLabel: string; blocked: boolean }[] = [];
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850">
	<div class="flex items-center justify-between">
		<div class="text-sm font-medium">{$i18n.t('Ce que l’agent a fait')}</div>
		<a href="/workspace/tasks" class="text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
			>{$i18n.t('Voir les tâches')} →</a
		>
	</div>

	{#if loading}
		<div class="flex justify-center py-6"><Spinner className="size-5" /></div>
	{:else if unavailable}
		<div class="text-xs text-gray-500 py-2">{$i18n.t('Indisponible pour le moment.')}</div>
	{:else}
		{#if counts.length > 0}
			<div class="flex flex-wrap gap-2">
				{#each counts as c (c.label)}
					<span class="text-xs px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-850 text-gray-700 dark:text-gray-300">
						{c.n} · {$i18n.t(c.label)}
					</span>
				{/each}
			</div>
		{/if}

		{#if recent.length === 0}
			<div class="text-xs text-gray-500 py-2">{$i18n.t('Aucune tâche pour l’instant.')}</div>
		{:else}
			<div class="flex flex-col divide-y divide-gray-100 dark:divide-gray-850">
				{#each recent as t (t.title)}
					<div class="flex items-center justify-between gap-3 py-2 text-sm">
						<span class="truncate text-gray-700 dark:text-gray-200">{t.title}</span>
						<span
							class="flex-none text-xs {t.blocked
								? 'text-amber-600 dark:text-amber-400'
								: 'text-gray-500'}">{$i18n.t(t.statusLabel)}</span
						>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>
