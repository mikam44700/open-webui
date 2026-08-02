<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import type { PlatformRow } from '$lib/engine/health';
	import Card from './Card.svelte';
	import StateBadge from './StateBadge.svelte';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let platforms: PlatformRow[] = [];
	export let loading = false;

	$: connected = platforms.filter((platform) => platform.state === 'ok').length;
</script>

<Card title={$i18n.t('Connected platforms')} {loading}>
	<span slot="action" class="tabular-nums text-xs text-gray-500 dark:text-gray-400">
		{#if platforms.length}{connected}/{platforms.length}{/if}
	</span>

	{#if platforms.length === 0}
		<div class="py-2 text-xs text-gray-500">
			{$i18n.t('The engine did not report any messaging platform.')}
		</div>
	{:else}
		<div class="flex flex-col">
			{#each platforms as platform (platform.name)}
				<div class="flex items-center justify-between gap-4 py-1.5 text-sm">
					<span class="min-w-0 truncate capitalize text-gray-700 dark:text-gray-200">
						{platform.name.replaceAll('_', ' ')}
					</span>
					<StateBadge
						state={platform.state}
						activeLabel="Connected"
						downLabel="Not connected"
						showIdle
					/>
				</div>
			{/each}
		</div>
	{/if}
</Card>
