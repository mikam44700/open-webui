<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { ViewMode } from '$lib/calendar/calendar-views';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{ prev: void; next: void; today: void; mode: ViewMode }>();

	export let title: string;
	export let mode: ViewMode;

	const MODES: { id: ViewMode; label: string }[] = [
		{ id: 'day', label: 'Jour' },
		{ id: 'week', label: 'Semaine' },
		{ id: 'month', label: 'Mois' }
	];
</script>

<div class="flex flex-wrap items-center justify-between gap-3 mb-3">
	<div class="text-lg font-semibold">{title}</div>

	<div class="flex items-center gap-2">
		<!-- Sélecteur Jour / Semaine / Mois -->
		<div class="inline-flex rounded-xl bg-gray-100 dark:bg-gray-850 p-0.5">
			{#each MODES as m (m.id)}
				<button
					type="button"
					on:click={() => dispatch('mode', m.id)}
					aria-pressed={mode === m.id}
					class="px-3 py-1 rounded-lg text-sm transition
						{mode === m.id
							? 'bg-white dark:bg-gray-700 shadow-sm font-medium'
							: 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'}"
				>
					{$i18n.t(m.label)}
				</button>
			{/each}
		</div>

		<!-- Navigation -->
		<button
			class="px-2.5 py-1.5 rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-850 transition"
			on:click={() => dispatch('today')}
		>
			{$i18n.t('Aujourd’hui')}
		</button>
		<div class="flex items-center">
			<button
				class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				aria-label={$i18n.t('Précédent')}
				on:click={() => dispatch('prev')}
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
			</button>
			<button
				class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				aria-label={$i18n.t('Suivant')}
				on:click={() => dispatch('next')}
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6" /></svg>
			</button>
		</div>
	</div>
</div>
