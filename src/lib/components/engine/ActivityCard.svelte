<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import type { ActivityCounters } from '$lib/engine/health';
	import Card from './Card.svelte';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let counters: ActivityCounters = {
		activeAgents: 0,
		apiRuns: 0,
		delegations: 0,
		pendingCompletions: 0
	};
	export let busy = false;
	export let loading = false;

	$: metrics = [
		{ labelKey: 'Active agents', value: counters.activeAgents },
		{ labelKey: 'Requests in progress', value: counters.apiRuns },
		{ labelKey: 'Delegated tasks', value: counters.delegations },
		{ labelKey: 'Waiting in queue', value: counters.pendingCompletions }
	];
</script>

<Card title={$i18n.t('Current activity')} {loading}>
	<div class="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-4">
		{#each metrics as metric (metric.labelKey)}
			<div class="min-w-0 rounded-xl bg-gray-50 p-3 dark:bg-gray-850">
				<div
					class="tabular-nums text-xl font-semibold tracking-tight text-gray-900 dark:text-white"
				>
					{metric.value}
				</div>
				<div class="mt-1 text-pretty text-xs text-gray-500">{$i18n.t(metric.labelKey)}</div>
			</div>
		{/each}
	</div>

	<p class="mt-1 text-pretty text-xs text-gray-500 dark:text-gray-400">
		{busy
			? $i18n.t('Hermes is currently working on a request.')
			: $i18n.t('Hermes is ready for a new request.')}
	</p>
</Card>
