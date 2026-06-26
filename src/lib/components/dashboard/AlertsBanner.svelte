<script lang="ts">
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import type { Alert } from '$lib/dashboard/alerts';

	const i18n = getContext('i18n');

	export let alerts: Alert[] = [];
	export let loading = false;

	const tone: Record<string, string> = {
		critical: 'border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/30',
		warning: 'border-amber-200 dark:border-amber-900/50 bg-amber-50 dark:bg-amber-950/30',
		info: 'border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-950/30'
	};
	const dot: Record<string, string> = {
		critical: 'bg-red-500',
		warning: 'bg-amber-500',
		info: 'bg-blue-500'
	};
</script>

{#if loading}
	<div class="flex items-center gap-2 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 text-sm text-gray-500">
		<Spinner className="size-4" />
		{$i18n.t('Vérification de l’état du système…')}
	</div>
{:else if alerts.length === 0}
	<div
		class="flex items-center gap-2 p-4 rounded-2xl border border-green-200 dark:border-green-900/50 bg-green-50 dark:bg-green-950/30"
	>
		<span class="inline-block size-2 rounded-full bg-green-500"></span>
		<span class="text-sm font-medium text-green-700 dark:text-green-300">{$i18n.t('Tout est opérationnel')}</span>
	</div>
{:else}
	<div class="flex flex-col gap-2">
		<div class="text-sm font-medium">{$i18n.t('Demande votre attention')}</div>
		{#each alerts as a (a.message)}
			<a
				href={a.href}
				class="flex items-center justify-between gap-3 p-3 rounded-xl border {tone[a.severity]} transition hover:opacity-90"
			>
				<span class="flex items-center gap-2 text-sm">
					<span class="inline-block size-2 rounded-full {dot[a.severity]}"></span>
					{$i18n.t(a.message)}
				</span>
				<span class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Résoudre')} →</span>
			</a>
		{/each}
	</div>
{/if}
