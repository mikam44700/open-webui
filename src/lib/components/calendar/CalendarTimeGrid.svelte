<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import type { CalendarEvent } from '$lib/apis/calendar-hermes';
	import { bucketEventsByDay, dayKey, parseLocal } from '$lib/calendar/month-grid';
	import { layoutDayEvents, type TimedLayout } from '$lib/calendar/day-layout';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher<{
		event: CalendarEvent;
		slot: { date: Date; startLocal: string };
	}>();

	export let days: Date[] = []; // 1 jour (vue Jour) ou 7 (vue Semaine)
	export let events: CalendarEvent[] = [];
	export let today: Date = new Date();

	const HOUR_H = 48; // px par heure
	const HOURS = Array.from({ length: 24 }, (_, i) => i);

	const SOURCE_TINT: Record<string, string> = {
		google: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-500/20 dark:text-blue-200 dark:border-blue-500/40',
		outlook: 'bg-cyan-100 text-cyan-800 border-cyan-300 dark:bg-cyan-500/20 dark:text-cyan-200 dark:border-cyan-500/40',
		calendly: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-500/20 dark:text-amber-200 dark:border-amber-500/40'
	};
	const tint = (src?: string) =>
		(src && SOURCE_TINT[src]) ||
		'bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-700/50 dark:text-gray-100 dark:border-gray-600';

	const isAllDay = (e: CalendarEvent) => e.all_day || !e.start.includes('T');
	const hhmm = (iso: string): string => {
		const dt = parseLocal(iso);
		return dt ? dt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '';
	};
	const sameDay = (a: Date, b: Date) => dayKey(a) === dayKey(b);
	const nowMin = today.getHours() * 60 + today.getMinutes();

	type DayColumn = { date: Date; allDay: CalendarEvent[]; timed: TimedLayout<CalendarEvent>[] };

	// TOUT est réactif : Svelte recalcule dès que `days` OU `events` change (sinon, en
	// réutilisant le même composant d'une vue à l'autre, l'affichage restait figé).
	$: byDay = bucketEventsByDay(events);
	$: columns = days.map((d): DayColumn => {
		const evs = byDay[dayKey(d)] ?? [];
		return {
			date: d,
			allDay: evs.filter(isAllDay),
			timed: layoutDayEvents(
				evs.filter((e) => !isAllDay(e)),
				d
			)
		};
	});
	$: hasAllDay = columns.some((c) => c.allDay.length > 0);
	$: gridCols = `56px repeat(${days.length}, minmax(0, 1fr))`;

	let scroller: HTMLDivElement;
	onMount(() => {
		if (scroller) scroller.scrollTop = 7 * HOUR_H; // ouvre vers 7 h du matin
	});
</script>

<div class="rounded-2xl border border-gray-100 dark:border-gray-850 overflow-hidden bg-white dark:bg-gray-900">
	<!-- Un SEUL conteneur scrollable : en-tête et corps partagent la même largeur
	     (même réduction par la scrollbar) → colonnes parfaitement alignées. -->
	<div bind:this={scroller} class="overflow-y-auto max-h-[600px]">
		<!-- En-tête (+ journée entière) collé en haut au défilement -->
		<div class="sticky top-0 z-10 bg-white dark:bg-gray-900">
			<!-- En-tête des jours -->
			<div class="grid border-b border-gray-200 dark:border-gray-800" style="grid-template-columns: {gridCols}">
				<div class="border-r border-gray-200 dark:border-gray-800"></div>
				{#each columns as c (dayKey(c.date))}
					<div class="py-2 text-center border-r border-gray-200 dark:border-gray-800 last:border-r-0">
						<div class="text-[11px] uppercase text-gray-400">
							{c.date.toLocaleDateString('fr-FR', { weekday: 'short' })}
						</div>
						<div class="mt-0.5 flex justify-center">
							<span
								class="inline-flex items-center justify-center size-7 rounded-full text-sm
									{sameDay(c.date, today) ? 'bg-black text-white dark:bg-white dark:text-black font-semibold' : 'text-gray-700 dark:text-gray-200'}"
							>
								{c.date.getDate()}
							</span>
						</div>
					</div>
				{/each}
			</div>

			<!-- Ligne « journée entière » (seulement si nécessaire) -->
			{#if hasAllDay}
				<div class="grid border-b border-gray-200 dark:border-gray-800" style="grid-template-columns: {gridCols}">
					<div class="px-1 py-1 text-[10px] text-gray-400 border-r border-gray-200 dark:border-gray-800 flex items-center justify-end">
						{$i18n.t('Journée')}
					</div>
					{#each columns as c (dayKey(c.date))}
						<div class="p-1 border-r border-gray-200 dark:border-gray-800 last:border-r-0 flex flex-col gap-1 min-h-[28px]">
							{#each c.allDay as e (e.id)}
								<button
									type="button"
									on:click={() => dispatch('event', e)}
									class="block truncate rounded-md border px-1.5 py-0.5 text-[11px] text-left {tint(e.source)}"
									title={e.title}
								>
									{e.title}
								</button>
							{/each}
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Corps horaire -->
		<div class="grid relative" style="grid-template-columns: {gridCols}">
			<!-- Colonne des heures -->
			<div class="border-r border-gray-200 dark:border-gray-800">
				{#each HOURS as h}
					<div class="relative text-right pr-2" style="height: {HOUR_H}px">
						<span class="absolute -top-2 right-2 text-[10px] text-gray-400">
							{h === 0 ? '' : `${String(h).padStart(2, '0')}:00`}
						</span>
					</div>
				{/each}
			</div>

			<!-- Colonnes des jours -->
			{#each columns as c (dayKey(c.date))}
				<div class="relative border-r border-gray-200 dark:border-gray-800 last:border-r-0">
					<!-- Fond : cases horaires cliquables -->
					{#each HOURS as h}
						<button
							type="button"
							aria-label={$i18n.t('Créer un événement')}
							on:click={() =>
								dispatch('slot', {
									date: c.date,
									startLocal: `${dayKey(c.date)}T${String(h).padStart(2, '0')}:00`
								})}
							class="block w-full border-t border-gray-200 dark:border-gray-700/60 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition"
							style="height: {HOUR_H}px"
						></button>
					{/each}

					<!-- Trait « maintenant » sur la colonne du jour courant -->
					{#if sameDay(c.date, today)}
						<div class="absolute left-0 right-0 pointer-events-none" style="top: {(nowMin / 60) * HOUR_H}px">
							<div class="h-px bg-red-500"></div>
							<div class="absolute -left-1 -top-1 size-2 rounded-full bg-red-500"></div>
						</div>
					{/if}

					<!-- Événements horodatés positionnés -->
					{#each c.timed as p (p.event.id)}
						<button
							type="button"
							on:click={() => dispatch('event', p.event)}
							title={p.event.title}
							class="absolute rounded-md border px-1.5 py-0.5 text-[11px] text-left overflow-hidden {tint(p.event.source)}"
							style="
								top: {(p.startMin / 60) * HOUR_H}px;
								height: {Math.max(((p.endMin - p.startMin) / 60) * HOUR_H - 2, 20)}px;
								left: calc({(p.lane / p.lanes) * 100}% + 2px);
								width: calc({100 / p.lanes}% - 4px);
							"
						>
							<div class="font-medium truncate leading-tight">{p.event.title}</div>
							<div class="opacity-70 truncate leading-tight">{hhmm(p.event.start)}</div>
						</button>
					{/each}
				</div>
			{/each}
		</div>
	</div>
</div>
