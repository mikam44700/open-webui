<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import {
		getCalendarSources,
		getEvents,
		createEvent,
		deleteEvent,
		type CalendarEvent,
		type CalendarSource
	} from '$lib/apis/calendar-hermes';
	import { validateEventForm } from '$lib/calendar/event-form';

	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import CalendarConnectPrompt from './CalendarConnectPrompt.svelte';
	import CalendarMonthGrid from './CalendarMonthGrid.svelte';
	import CalendarTimeGrid from './CalendarTimeGrid.svelte';
	import CalendarViewHeader from './CalendarViewHeader.svelte';
	import CalendarSourceBar from './CalendarSourceBar.svelte';
	import PageHeader from '$lib/components/common/PageHeader.svelte';
	import { CALENDAR_SOURCE_LOGO } from '$lib/utils/integrationLogos';
	import { rangeFor, shiftAnchor, titleFor, weekDays, type ViewMode } from '$lib/calendar/calendar-views';

	const i18n = getContext('i18n');

	// Fuseau du navigateur (ex. « Europe/Paris ») : indispensable pour Outlook et Calendly,
	// qui raisonnent en UTC côté API. Google gère son propre fuseau via la skill.
	const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
	const LS_KEY = 'agentos.calendar.source';

	let loading = true;
	let unavailable = false;
	let sources: CalendarSource[] = [];
	let activeSource: string = '';
	let events: CalendarEvent[] = []; // prochains événements (liste sous la grille)

	// Grille « mois » : sa propre fenêtre de dates, rechargée à chaque navigation.
	let viewMode: ViewMode = 'month';
	let anchor = new Date(); // date de référence de la vue courante
	let gridEvents: CalendarEvent[] = [];

	$: gridTitle = titleFor(viewMode, anchor);
	$: gridDays = viewMode === 'week' ? weekDays(anchor) : [anchor];

	let showModal = false;
	let form = { title: '', startLocal: '', endLocal: '', location: '' };
	let saving = false;

	let showDeleteConfirm = false;
	let deleteTarget: CalendarEvent | null = null;

	$: connectedSources = sources.filter((s) => s.connected);
	$: activeSourceObj = sources.find((s) => s.id === activeSource) ?? null;
	$: canWrite = !!activeSourceObj?.can_write;
	$: activeLabel = activeSourceObj?.label ?? 'calendrier';

	const subtitle = (src: CalendarSource | null): string => {
		if (!src) return $i18n.t('Votre agenda, géré par Agent OS.');
		if (src.id === 'calendly') return $i18n.t('Vos rendez-vous Calendly, dans Agent OS.');
		return $i18n.t('Votre agenda {{name}}, géré par Agent OS.', { name: src.label });
	};

	const loadEvents = async () => {
		if (!activeSource) {
			events = [];
			return;
		}
		const now = new Date();
		const end = new Date(now.getTime() + 60 * 24 * 3600 * 1000);
		const res = await getEvents(
			localStorage.token,
			activeSource,
			now.toISOString(),
			end.toISOString(),
			tz
		);
		events = res?.events ?? [];
	};

	// Charge les événements du mois affiché (fenêtre = toute la grille 6 semaines).
	const loadGrid = async () => {
		if (!activeSource) {
			gridEvents = [];
			return;
		}
		const { start, end } = rangeFor(viewMode, anchor);
		const res = await getEvents(localStorage.token, activeSource, start, end, tz);
		gridEvents = res?.events ?? [];
	};

	// Un échec de grille ne doit pas casser la page : on garde la liste.
	const reloadGrid = async () => {
		try {
			await loadGrid();
		} catch (err) {
			gridEvents = [];
		}
	};

	const prev = () => {
		anchor = shiftAnchor(viewMode, anchor, -1);
		reloadGrid();
	};
	const next = () => {
		anchor = shiftAnchor(viewMode, anchor, 1);
		reloadGrid();
	};
	const goToday = () => {
		anchor = new Date();
		reloadGrid();
	};
	const setMode = (e: CustomEvent<ViewMode>) => {
		viewMode = e.detail;
		reloadGrid();
	};

	// Clic sur un jour de la grille → pré-remplit le formulaire (09:00–10:00) et ouvre la modale.
	const onDayClick = (e: CustomEvent<{ key: string; date: Date }>) => {
		if (!canWrite) return;
		const day = e.detail.key; // « YYYY-MM-DD »
		form = { title: '', startLocal: `${day}T09:00`, endLocal: `${day}T10:00`, location: '' };
		showModal = true;
	};

	// Clic sur un événement → ouvre le lien natif (Google Agenda, etc.) s'il existe.
	const onEventClick = (e: CustomEvent<CalendarEvent>) => {
		if (e.detail.link) window.open(e.detail.link, '_blank', 'noopener');
	};

	// Clic sur un créneau horaire (vues Jour/Semaine) → nouvel événement pré-rempli (+1 h).
	const onSlotClick = (e: CustomEvent<{ date: Date; startLocal: string }>) => {
		if (!canWrite) return;
		const start = new Date(e.detail.startLocal);
		const end = new Date(start.getTime() + 60 * 60 * 1000);
		const pad = (n: number) => String(n).padStart(2, '0');
		const fmt = (d: Date) =>
			`${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
		form = { title: '', startLocal: e.detail.startLocal, endLocal: fmt(end), location: '' };
		showModal = true;
	};

	// « Ajouter un calendrier » → onglet Intégrations (même parcours que l'écran de connexion).
	const openIntegrations = () => goto('/connectors?tab=integrations');

	const load = async () => {
		loading = true;
		unavailable = false;
		try {
			const res = await getCalendarSources(localStorage.token);
			sources = res?.sources ?? [];
			const connected = sources.filter((s) => s.connected);
			if (connected.length === 0) {
				activeSource = '';
				events = [];
				gridEvents = [];
				return;
			}
			// Restaure le dernier calendrier consulté s'il est toujours connecté, sinon la
			// source par défaut (1re connectée).
			const saved = localStorage.getItem(LS_KEY);
			const savedOk = saved && connected.some((s) => s.id === saved);
			activeSource = savedOk ? (saved as string) : (res?.default ?? connected[0].id);
			await loadEvents();
			await loadGrid();
		} catch (err: any) {
			if (typeof err?.code === 'string' && err.code.endsWith('_not_connected')) {
				// La source a été déconnectée entre-temps : on recharge la liste des sources.
				events = [];
			} else {
				unavailable = true;
			}
		} finally {
			loading = false;
		}
	};

	const switchSource = async (id: string) => {
		if (id === activeSource) return;
		activeSource = id;
		localStorage.setItem(LS_KEY, id);
		loading = true;
		unavailable = false;
		try {
			await loadEvents();
			await loadGrid();
		} catch (err) {
			unavailable = true;
		} finally {
			loading = false;
		}
	};

	const submit = async () => {
		const v = validateEventForm(form);
		if (!v.ok) {
			toast.error(v.error);
			return;
		}
		saving = true;
		try {
			await createEvent(localStorage.token, { ...v.body, source: activeSource, tz });
			toast.success($i18n.t('Événement ajouté à votre agenda'));
			showModal = false;
			form = { title: '', startLocal: '', endLocal: '', location: '' };
			await loadEvents();
			await loadGrid();
		} catch (err) {
			toast.error(typeof err === 'string' ? err : $i18n.t('Ajout impossible'));
		} finally {
			saving = false;
		}
	};

	const confirmDelete = (e: CalendarEvent) => {
		deleteTarget = e;
		showDeleteConfirm = true;
	};

	const doDelete = async () => {
		if (!deleteTarget) return;
		try {
			await deleteEvent(localStorage.token, deleteTarget.id, activeSource);
			events = events.filter((x) => x.id !== deleteTarget!.id);
			gridEvents = gridEvents.filter((x) => x.id !== deleteTarget!.id);
			toast.success($i18n.t('Événement supprimé'));
		} catch (err) {
			toast.error(typeof err === 'string' ? err : $i18n.t('Suppression impossible'));
		} finally {
			deleteTarget = null;
		}
	};

	onMount(load);
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Supprimer cet événement ?')}
	on:confirm={doDelete}
>
	<div class="text-sm text-gray-500">{deleteTarget?.title}</div>
</ConfirmDialog>

<Modal bind:show={showModal} size="sm">
	<div class="px-5 py-4">
		<div class="text-lg font-medium mb-3">{$i18n.t('Nouvel événement')}</div>
		<div class="flex flex-col gap-3">
			<label class="text-sm">
				<span class="text-gray-600 dark:text-gray-300">{$i18n.t('Titre')}</span>
				<input class="w-full mt-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 outline-none text-sm" bind:value={form.title} placeholder={$i18n.t('Ex : Rendez-vous client')} />
			</label>
			<div class="grid grid-cols-2 gap-2 text-sm">
				<label>
					<span class="text-gray-600 dark:text-gray-300">{$i18n.t('Début')}</span>
					<input type="datetime-local" class="w-full mt-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm" bind:value={form.startLocal} />
				</label>
				<label>
					<span class="text-gray-600 dark:text-gray-300">{$i18n.t('Fin')}</span>
					<input type="datetime-local" class="w-full mt-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 text-sm" bind:value={form.endLocal} />
				</label>
			</div>
			<label class="text-sm">
				<span class="text-gray-600 dark:text-gray-300">{$i18n.t('Lieu (optionnel)')}</span>
				<input class="w-full mt-1 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 outline-none text-sm" bind:value={form.location} />
			</label>
			{#if activeSourceObj}
				<div class="text-[11px] text-gray-400">
					{$i18n.t('Sera ajouté à : {{name}}', { name: activeLabel })}
				</div>
			{/if}
		</div>
		<div class="flex justify-end gap-2 mt-4">
			<button class="px-3 py-1.5 rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (showModal = false)}>{$i18n.t('Annuler')}</button>
			<button class="px-3 py-1.5 rounded-lg text-sm btn-premium bg-black text-white dark:bg-white dark:text-black disabled:opacity-50" disabled={saving} on:click={submit}>{$i18n.t('Ajouter')}</button>
		</div>
	</div>
</Modal>

<div class="flex flex-col w-full">
	<div class="flex justify-between items-center mb-4 gap-3">
		<div class="min-w-0">
			<PageHeader
				eyebrow={$i18n.t('Calendrier')}
				title={$i18n.t('Tout votre agenda, piloté pour vous')}
				description={subtitle(activeSourceObj)}
			/>
		</div>
		<div class="flex items-center gap-2">
			{#if canWrite && connectedSources.length > 0 && !unavailable}
				<button class="px-3 py-1.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black text-sm font-medium whitespace-nowrap" on:click={() => (showModal = true)}>
					+ {$i18n.t('Nouvel événement')}
				</button>
			{/if}
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-20"><Spinner className="size-5" /></div>
	{:else if unavailable}
		<div class="flex flex-col items-center justify-center py-20 text-center">
			<div class="size-12 rounded-2xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center mb-3">
				<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" class="text-amber-500">
					<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
					<path d="M12 9v4M12 17h.01" />
				</svg>
			</div>
			<div class="font-medium">{$i18n.t('Agenda momentanément indisponible')}</div>
			<button class="mt-3 text-sm underline text-gray-500 hover:text-gray-900 dark:hover:text-gray-100" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else if connectedSources.length === 0}
		<CalendarConnectPrompt />
	{:else}
		<!-- Barre « Mes calendriers » : basculer entre calendriers connectés + en ajouter un -->
		<CalendarSourceBar
			{sources}
			{activeSource}
			on:switch={(e) => switchSource(e.detail)}
			on:connect={openIntegrations}
		/>

		<!-- En-tête partagé : sélecteur Jour/Semaine/Mois + navigation -->
		<CalendarViewHeader
			title={gridTitle}
			mode={viewMode}
			on:mode={setMode}
			on:prev={prev}
			on:next={next}
			on:today={goToday}
		/>

		<!-- Vue courante (toujours affichée, même sans événement) -->
		{#if viewMode === 'month'}
			<CalendarMonthGrid
				events={gridEvents}
				year={anchor.getFullYear()}
				month={anchor.getMonth()}
				on:day={onDayClick}
				on:event={onEventClick}
			/>
		{:else}
			<CalendarTimeGrid
				days={gridDays}
				events={gridEvents}
				on:slot={onSlotClick}
				on:event={onEventClick}
			/>
		{/if}

		<!-- Prochains événements, sous la grille -->
		<div class="mt-6">
			<div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">
				{$i18n.t('Prochains événements')}
			</div>
			{#if events.length === 0}
				<div class="flex items-center gap-2 px-4 py-4 rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 text-sm text-gray-400">
					<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="3" /><path d="M8 2v4M16 2v4M3 10h18" /></svg>
					{$i18n.t('Aucun événement à venir. Votre agenda est à jour.')}
				</div>
			{:else}
				<div class="grid gap-2">
					{#each events as e (e.id)}
				<div class="flex items-center gap-3 px-4 py-3 rounded-2xl border border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850/40 transition">
					{#if e.source && CALENDAR_SOURCE_LOGO[e.source]}
						<div class="size-8 shrink-0 rounded-lg bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-1.5">
							<img src={CALENDAR_SOURCE_LOGO[e.source]} alt={e.source} class="max-w-full max-h-full object-contain" />
						</div>
					{/if}
					<div class="flex-1 min-w-0">
						<div class="text-sm font-medium truncate">{e.title}</div>
						<div class="text-[11px] text-gray-400 mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5">
							<span class="inline-flex items-center gap-1">
								<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
								{e.when_label}
							</span>
							{#if e.location}
								<span class="inline-flex items-center gap-1 min-w-0">
									<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="shrink-0"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></svg>
									<span class="truncate">{e.location}</span>
								</span>
							{/if}
						</div>
					</div>
					{#if canWrite}
						<Tooltip content={$i18n.t('Supprimer')}>
							<button class="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors" on:click={() => confirmDelete(e)} aria-label={$i18n.t('Supprimer')}>
								<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M10 11v6M14 11v6" /></svg>
							</button>
						</Tooltip>
					{/if}
				</div>
			{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>
