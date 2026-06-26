<script lang="ts">
	import { getContext } from 'svelte';
	import {
		onboardingProgress,
		onboardingComplete,
		type OnboardingStep
	} from '$lib/onboarding/steps';

	const i18n = getContext('i18n');

	export let steps: OnboardingStep[] = [];

	$: done = onboardingProgress(steps);
	$: complete = steps.length > 0 && onboardingComplete(steps);
</script>

{#if steps.length > 0}
	{#if complete}
		<div
			class="flex items-center gap-2 p-3 rounded-2xl border border-green-200 dark:border-green-900/50 bg-green-50 dark:bg-green-950/30"
		>
			<span class="inline-block size-2 rounded-full bg-green-500"></span>
			<span class="text-sm font-medium text-green-700 dark:text-green-300"
				>{$i18n.t('Configuration terminée')}</span
			>
		</div>
	{:else}
		<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850">
			<div class="flex items-center justify-between">
				<div class="text-sm font-medium">{$i18n.t('Mise en route')}</div>
				<span class="text-xs text-gray-500">{done}/{steps.length}</span>
			</div>

			<div class="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-850 overflow-hidden">
				<div class="h-full bg-black dark:bg-white transition-all" style="width: {(done / steps.length) * 100}%"></div>
			</div>

			<div class="flex flex-col divide-y divide-gray-100 dark:divide-gray-850 mt-1">
				{#each steps as s (s.id)}
					<div class="flex items-center justify-between gap-3 py-2">
						<span class="flex items-start gap-2 min-w-0">
							{#if s.done}
								<span class="flex-none mt-0.5 text-green-600 dark:text-green-400">✓</span>
							{:else}
								<span class="flex-none mt-0.5 inline-block size-2 rounded-full bg-gray-300 dark:bg-gray-600"></span>
							{/if}
							<span class="flex flex-col min-w-0">
								<span class="text-sm {s.done ? 'text-gray-400 line-through' : 'text-gray-800 dark:text-gray-100'}"
									>{$i18n.t(s.label)}</span
								>
								{#if !s.done}
									<span class="text-xs text-gray-500">{$i18n.t(s.hint)}</span>
								{/if}
							</span>
						</span>
						{#if !s.done}
							<a
								href={s.href}
								class="flex-none text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								>{$i18n.t('Faire')}</a
							>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	{/if}
{/if}
