<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { CalendarEvent } from '$lib/apis/calendar-hermes';
	import {
		buildMonthMatrix,
		bucketEventsByDay,
		monthLabel,
		parseLocal,
		WEEKDAY_LABELS,
		type DayCell
	} from '$lib/calendar/month-grid';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{
		prev: void;
		next: void;
		today: void;
		day: { key: string; date: Date };
		event: CalendarEvent;
	}>();

	export let events: CalendarEvent[] = [];
	export let year: number;
	export let month: number; // 0-indexé
	export let today: Date = new Date();

	const MAX_CHIPS = 3;

	// Teinte par source : cohérent avec les logos, lisible en clair comme en sombre.
	const SOURCE_TINT: Record<string, string> = {
		google: 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300',
		outlook: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/15 dark:text-cyan-300',
		calendly: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300'
	};
	const tint = (src?: string) =>
		(src && SOURCE_TINT[src]) || 'bg-gray-100 text-gray-700 dark:bg-gray-700/40 dark:text-gray-200';

	// Heure « HH:MM » d'un événement horodaté (rien pour une journée entière).
	const timePrefix = (e: CalendarEvent): string => {
		if (e.all_day || !e.start.includes('T')) return '';
		const d = parseLocal(e.start);
		if (!d) return '';
		return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
	};

	$: weeks = buildMonthMatrix(year, month, today);
	$: byDay = bucketEventsByDay(events);
	$: label = monthLabel(year, month);

	const eventsFor = (cell: DayCell): CalendarEvent[] => byDay[cell.key] ?? [];
</script>

<div class="rounded-2xl border border-gray-100 dark:border-gray-850 overflow-hidden bg-white dark:bg-gray-900">
	<!-- Barre de navigation du mois -->
	<div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-850">
		<div class="text-base font-semibold capitalize">{label}</div>
		<div class="flex items-center gap-1">
			<button
				class="px-2.5 py-1 rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				on:click={() => dispatch('today')}
			>
				{$i18n.t('Aujourd’hui')}
			</button>
			<button
				class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				aria-label={$i18n.t('Mois précédent')}
				on:click={() => dispatch('prev')}
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6" /></svg>
			</button>
			<button
				class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				aria-label={$i18n.t('Mois suivant')}
				on:click={() => dispatch('next')}
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6" /></svg>
			</button>
		</div>
	</div>

	<!-- En-tête des jours -->
	<div class="grid grid-cols-7 text-center text-[11px] font-medium text-gray-400 border-b border-gray-100 dark:border-gray-850">
		{#each WEEKDAY_LABELS as d}
			<div class="py-2">{d}</div>
		{/each}
	</div>

	<!-- Grille des jours -->
	<div class="grid grid-cols-7">
		{#each weeks as week, wi}
			{#each week as cell (cell.key)}
				{@const dayEvents = eventsFor(cell)}
				<button
					type="button"
					on:click={() => dispatch('day', { key: cell.key, date: cell.date })}
					class="group relative text-left min-h-[92px] p-1.5 border-b border-r border-gray-100 dark:border-gray-850
						last:border-r-0 hover:bg-gray-50 dark:hover:bg-gray-850/40 transition
						{cell.inMonth ? '' : 'bg-gray-50/50 dark:bg-black/20'}
						{wi === weeks.length - 1 ? 'border-b-0' : ''}"
				>
					<div class="flex justify-end">
						<span
							class="inline-flex items-center justify-center size-6 rounded-full text-xs
								{cell.isToday
									? 'bg-black text-white dark:bg-white dark:text-black font-semibold'
									: cell.inMonth
										? 'text-gray-700 dark:text-gray-200'
										: 'text-gray-300 dark:text-gray-600'}"
						>
							{cell.date.getDate()}
						</span>
					</div>

					<div class="mt-1 flex flex-col gap-1">
						{#each dayEvents.slice(0, MAX_CHIPS) as e (e.id)}
							<span
								class="block truncate rounded-md px-1.5 py-0.5 text-[11px] leading-tight {tint(e.source)}"
								title={e.title}
							>
								{#if timePrefix(e)}<span class="opacity-70 mr-1">{timePrefix(e)}</span>{/if}{e.title}
							</span>
						{/each}
						{#if dayEvents.length > MAX_CHIPS}
							<span class="text-[10px] text-gray-400 pl-1">
								+{dayEvents.length - MAX_CHIPS} {$i18n.t('autres')}
							</span>
						{/if}
					</div>
				</button>
			{/each}
		{/each}
	</div>
</div>
