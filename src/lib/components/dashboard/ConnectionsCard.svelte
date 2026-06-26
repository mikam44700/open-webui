<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let loading = false;
	export let unavailable = false;
	/** Libellé du cerveau actif, ou null si aucun. */
	export let activeBrainLabel: string | null = null;
	/** Intégrations : libellé + connecté (jamais de secret). */
	export let integrations: { label: string; connected: boolean }[] = [];
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850">
	<div class="flex items-center justify-between">
		<div class="text-sm font-medium">{$i18n.t('Ce qui est connecté')}</div>
		<a href="/connectors" class="text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
			>{$i18n.t('Gérer')} →</a
		>
	</div>

	{#if loading}
		<div class="flex justify-center py-6"><Spinner className="size-5" /></div>
	{:else if unavailable}
		<div class="text-xs text-gray-500 py-2">{$i18n.t('Indisponible pour le moment.')}</div>
	{:else}
		<!-- Cerveau actif -->
		<a
			href="/providers"
			class="flex items-center justify-between py-2 text-sm border-b border-gray-100 dark:border-gray-850 hover:opacity-80"
		>
			<span class="text-gray-700 dark:text-gray-200">{$i18n.t('Modèle IA actif')}</span>
			{#if activeBrainLabel}
				<span class="text-xs font-medium text-gray-900 dark:text-gray-100">{activeBrainLabel}</span>
			{:else}
				<span class="text-xs text-amber-600 dark:text-amber-400">{$i18n.t('Aucun')}</span>
			{/if}
		</a>

		{#if integrations.length === 0}
			<div class="text-xs text-gray-500 py-2">
				{$i18n.t('Aucune intégration connectée pour l’instant.')}
				<a href="/connectors" class="underline">{$i18n.t('En connecter une')}</a>
			</div>
		{:else}
			<div class="flex flex-col">
				{#each integrations as it (it.label)}
					<div class="flex items-center justify-between py-1.5 text-sm">
						<span class="text-gray-700 dark:text-gray-200">{it.label}</span>
						{#if it.connected}
							<span class="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
								<span class="inline-block size-2 rounded-full bg-green-500"></span>{$i18n.t('Connecté')}
							</span>
						{:else}
							<span class="flex items-center gap-1.5 text-xs text-gray-500">
								<span class="inline-block size-2 rounded-full bg-gray-400 dark:bg-gray-600"></span>{$i18n.t(
									'Non connecté'
								)}
							</span>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>
