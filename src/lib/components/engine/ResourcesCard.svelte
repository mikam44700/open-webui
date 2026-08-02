<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import Card from './Card.svelte';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let model: string | null = null;
	export let skillCount: number | null = null;
	export let toolsetCount: number | null = null;
	export let loading = false;

	/** `null` = source non joignable. On l'affiche comme tel, jamais comme un zéro. */
	const countLabel = (value: number | null) => (value === null ? '—' : String(value));
</script>

<Card title={$i18n.t('What is connected')} {loading}>
	<a
		slot="action"
		href="/workspace"
		class="text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
	>
		{$i18n.t('Manage')} →
	</a>

	<div class="flex flex-col divide-y divide-gray-100 dark:divide-gray-850">
		<div class="flex items-center justify-between gap-3 py-2 text-sm">
			<span class="text-gray-700 dark:text-gray-200">{$i18n.t('Active model')}</span>
			{#if model}
				<span
					class="max-w-52 truncate text-xs font-medium text-gray-900 dark:text-gray-100"
					title={model}
				>
					{model}
				</span>
			{:else}
				<span class="text-xs text-amber-600 dark:text-amber-400">{$i18n.t('None')}</span>
			{/if}
		</div>

		<div class="flex items-center justify-between gap-3 py-2 text-sm">
			<span class="text-gray-700 dark:text-gray-200">{$i18n.t('Installed skills')}</span>
			<span class="tabular-nums text-xs font-medium text-gray-900 dark:text-gray-100">
				{countLabel(skillCount)}
			</span>
		</div>

		<div class="flex items-center justify-between gap-3 py-2 text-sm">
			<span class="text-gray-700 dark:text-gray-200">{$i18n.t('Configured tools')}</span>
			<span class="tabular-nums text-xs font-medium text-gray-900 dark:text-gray-100">
				{countLabel(toolsetCount)}
			</span>
		</div>
	</div>
</Card>
