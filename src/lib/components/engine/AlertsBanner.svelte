<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import type { EngineAlert } from '$lib/engine/health';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let alerts: EngineAlert[] = [];
	export let loading = false;
	export let lastChecked: Date | null = null;

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

	const messageOf = (alert: EngineAlert) =>
		$i18n.t(alert.messageKey, {
			...(alert.messageParams ?? {}),
			...(alert.componentKey ? { component: $i18n.t(alert.componentKey) } : {})
		});
</script>

{#if loading}
	<div
		class="flex items-center gap-2 rounded-2xl border border-gray-100 p-4 text-sm text-gray-500 dark:border-gray-850"
	>
		<Spinner className="size-4" />
		{$i18n.t('Checking the engine status…')}
	</div>
{:else if alerts.length === 0}
	<div
		class="flex items-center justify-between gap-3 rounded-2xl border border-green-200 bg-green-50 p-4 dark:border-green-900/50 dark:bg-green-950/30"
	>
		<span class="flex items-center gap-2">
			<span class="inline-block size-2 rounded-full bg-green-500"></span>
			<span class="text-sm font-medium text-green-700 dark:text-green-300">
				{$i18n.t('Everything is operational')}
			</span>
		</span>
		{#if lastChecked}
			<span class="shrink-0 text-xs text-green-700/80 dark:text-green-300/80">
				{lastChecked.toLocaleTimeString()}
			</span>
		{/if}
	</div>
{:else}
	<div class="flex flex-col gap-2">
		<div class="flex items-center justify-between gap-3">
			<div class="text-sm font-medium">{$i18n.t('Needs your attention')}</div>
			{#if lastChecked}
				<span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Last checked')}: {lastChecked.toLocaleTimeString()}
				</span>
			{/if}
		</div>

		{#each alerts as alert (alert.messageKey + (alert.componentKey ?? ''))}
			<svelte:element
				this={alert.href ? 'a' : 'div'}
				href={alert.href}
				role={alert.href ? undefined : 'listitem'}
				class="flex flex-col gap-1 rounded-xl border p-3 sm:flex-row sm:items-center sm:justify-between sm:gap-3 {tone[
					alert.severity
				]} {alert.href ? 'transition hover:opacity-90' : ''}"
			>
				<span class="flex items-center gap-2 text-sm">
					<span class="inline-block size-2 shrink-0 rounded-full {dot[alert.severity]}"></span>
					{messageOf(alert)}
				</span>

				{#if alert.href}
					<span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t('Resolve')} →
					</span>
				{:else if alert.hintKey}
					<span class="text-pretty text-xs text-gray-600 dark:text-gray-300 sm:text-right">
						{$i18n.t(alert.hintKey)}
					</span>
				{/if}
			</svelte:element>
		{/each}
	</div>
{/if}
