<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import type { DisplayState, EngineIssue } from '$lib/engine/health';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let state: DisplayState = 'unknown';
	export let issue: EngineIssue | null = null;
	export let lastChecked: Date | null = null;
	export let loading = false;

	const toneClass: Record<DisplayState, string> = {
		ok: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200',
		warning:
			'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200',
		down: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200',
		unknown:
			'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-200'
	};

	const dotClass: Record<DisplayState, string> = {
		ok: 'bg-emerald-500',
		warning: 'bg-amber-500',
		down: 'bg-red-500',
		unknown: 'bg-gray-400 dark:bg-gray-600'
	};
</script>

{#if loading}
	<div class="rounded-2xl border border-gray-200 p-4 dark:border-gray-800">
		<div class="h-4 w-32 rounded bg-gray-100 dark:bg-gray-800"></div>
		<div class="mt-3 h-3 w-64 max-w-full rounded bg-gray-100 dark:bg-gray-800"></div>
	</div>
{:else}
	<div
		class="flex flex-col gap-3 rounded-2xl border p-4 sm:flex-row sm:items-start sm:justify-between {toneClass[
			state
		]}"
		role="status"
		aria-live="polite"
	>
		<div class="flex items-start gap-3">
			<span class="mt-1 size-2.5 shrink-0 rounded-full {dotClass[state]}"></span>
			<div>
				{#if state === 'ok'}
					<div class="font-medium">{$i18n.t('Everything is operational')}</div>
					<div class="mt-0.5 text-pretty text-sm">
						{$i18n.t('Hermes Agent is ready. No action is required.')}
					</div>
				{:else if issue}
					<div class="font-medium">{$i18n.t(issue.titleKey)}</div>
					<div class="mt-0.5 text-pretty text-sm">
						{$i18n.t(issue.descriptionKey, issue.descriptionParams ?? {})}
					</div>
					{#if issue.hintKey}
						<div class="mt-2 text-pretty text-xs opacity-80">{$i18n.t(issue.hintKey)}</div>
					{/if}
				{/if}
			</div>
		</div>

		{#if lastChecked}
			<div class="shrink-0 text-xs opacity-80">
				{$i18n.t('Last checked')}: {lastChecked.toLocaleTimeString()}
			</div>
		{/if}
	</div>
{/if}
