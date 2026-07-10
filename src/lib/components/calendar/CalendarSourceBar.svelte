<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { CalendarSource } from '$lib/apis/calendar-hermes';
	import { CALENDAR_SOURCE_LOGO } from '$lib/utils/integrationLogos';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{ switch: string; connect: void }>();

	export let sources: CalendarSource[] = [];
	export let activeSource: string = '';

	$: connected = sources.filter((s) => s.connected);
	// Reste-t-il un calendrier connectable (non encore branché) ? Sinon, pas de bouton « Ajouter ».
	$: canAddMore = sources.some((s) => !s.connected);
</script>

<div class="flex flex-wrap items-center gap-2 mb-4">
	<span class="text-xs font-medium text-gray-400 mr-1">{$i18n.t('Mes calendriers')}</span>

	{#each connected as s (s.id)}
		<button
			type="button"
			on:click={() => dispatch('switch', s.id)}
			aria-pressed={s.id === activeSource}
			class="inline-flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-full border text-sm transition
				{s.id === activeSource
					? 'border-black dark:border-white bg-gray-100 dark:bg-gray-800 font-medium'
					: 'border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 text-gray-600 dark:text-gray-300'}"
		>
			{#if CALENDAR_SOURCE_LOGO[s.id]}
				<span class="size-5 rounded-md bg-white dark:bg-gray-900 flex items-center justify-center p-0.5">
					<img src={CALENDAR_SOURCE_LOGO[s.id]} alt={s.label} class="max-w-full max-h-full object-contain" />
				</span>
			{/if}
			{s.label}
			{#if s.id === activeSource}
				<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="text-green-500"><path d="M20 6 9 17l-5-5" /></svg>
			{/if}
		</button>
	{/each}

	{#if canAddMore}
		<button
			type="button"
			on:click={() => dispatch('connect')}
			class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-dashed
				border-gray-300 dark:border-gray-700 text-sm text-gray-500 dark:text-gray-400
				hover:border-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
		>
			<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14" /></svg>
			{$i18n.t('Ajouter un calendrier')}
		</button>
	{/if}
</div>
