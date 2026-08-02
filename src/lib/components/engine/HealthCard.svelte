<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import type { HealthRow } from '$lib/engine/health';
	import Card from './Card.svelte';
	import StateBadge from './StateBadge.svelte';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let rows: HealthRow[] = [];
	export let loading = false;

	const detailOf = (row: HealthRow) =>
		row.detailKey ? $i18n.t(row.detailKey, row.detailParams ?? {}) : (row.detail ?? '');
</script>

<Card title={$i18n.t('Engine health')} {loading}>
	<div class="flex flex-col divide-y divide-gray-100 dark:divide-gray-850">
		{#each rows as row (row.labelKey)}
			{@const detail = detailOf(row)}
			<div class="flex items-center justify-between gap-4 py-2 text-sm">
				<span class="text-gray-700 dark:text-gray-200">{$i18n.t(row.labelKey)}</span>
				<span class="flex min-w-0 items-center gap-2">
					{#if detail}
						<span class="max-w-36 truncate text-xs text-gray-400" title={detail}>{detail}</span>
					{/if}
					<StateBadge state={row.state} />
				</span>
			</div>
		{/each}
	</div>
</Card>
