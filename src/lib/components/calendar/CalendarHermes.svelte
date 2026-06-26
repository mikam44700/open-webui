<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import {
		getCalendarStatus,
		getEvents,
		createEvent,
		deleteEvent,
		type CalendarEvent
	} from '$lib/apis/calendar-hermes';
	import { validateEventForm } from '$lib/calendar/event-form';

	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let connected = false;
	let unavailable = false;
	let events: CalendarEvent[] = [];

	let showModal = false;
	let form = { title: '', startLocal: '', endLocal: '', location: '' };
	let saving = false;

	let showDeleteConfirm = false;
	let deleteTarget: CalendarEvent | null = null;

	const load = async () => {
		loading = true;
		unavailable = false;
		try {
			const status = await getCalendarStatus(localStorage.token);
			connected = !!status?.connected;
			if (!connected) {
				events = [];
				return;
			}
			// Fenêtre : maintenant -> +60 jours
			const now = new Date();
			const end = new Date(now.getTime() + 60 * 24 * 3600 * 1000);
			const res = await getEvents(localStorage.token, now.toISOString(), end.toISOString());
			events = res?.events ?? [];
		} catch (err: any) {
			// 409 google_not_connected géré comme "non connecté", sinon indisponible
			if (err?.error?.code === 'google_not_connected') {
				connected = false;
			} else {
				unavailable = true;
			}
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
			await createEvent(localStorage.token, v.body);
			toast.success($i18n.t('Événement ajouté à votre agenda'));
			showModal = false;
			form = { title: '', startLocal: '', endLocal: '', location: '' };
			await load();
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
			await deleteEvent(localStorage.token, deleteTarget.id);
			events = events.filter((x) => x.id !== deleteTarget!.id);
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
		</div>
		<div class="flex justify-end gap-2 mt-4">
			<button class="px-3 py-1.5 rounded-lg text-sm hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (showModal = false)}>{$i18n.t('Annuler')}</button>
			<button class="px-3 py-1.5 rounded-lg text-sm bg-black text-white dark:bg-white dark:text-black disabled:opacity-50" disabled={saving} on:click={submit}>{$i18n.t('Ajouter')}</button>
		</div>
	</div>
</Modal>

<div class="flex flex-col w-full">
	<div class="flex justify-between items-center mb-4">
		<div>
			<div class="text-xl font-medium">{$i18n.t('Calendrier')}</div>
			<div class="text-xs text-gray-500">{$i18n.t('Votre agenda Google, géré par Agent OS.')}</div>
		</div>
		{#if connected}
			<button class="px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium" on:click={() => (showModal = true)}>
				+ {$i18n.t('Nouvel événement')}
			</button>
		{/if}
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-20"><Spinner className="size-5" /></div>
	{:else if unavailable}
		<div class="flex flex-col items-center justify-center py-20 text-center">
			<div class="text-3xl mb-2">🔌</div>
			<div class="font-medium">{$i18n.t('Agenda momentanément indisponible')}</div>
			<button class="mt-3 text-sm underline" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else if !connected}
		<div class="flex flex-col items-center justify-center py-20 text-center">
			<div class="text-3xl mb-2">📅</div>
			<div class="font-medium">{$i18n.t('Connectez votre Google Agenda')}</div>
			<div class="text-xs text-gray-500 mt-1 max-w-md">
				{$i18n.t('Pour qu’Agent OS gère votre calendrier, connectez votre compte Google dans Intégrations.')}
			</div>
			<button class="mt-3 px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm" on:click={() => goto('/connectors')}>
				{$i18n.t('Ouvrir Intégrations')}
			</button>
		</div>
	{:else if events.length === 0}
		<div class="flex flex-col items-center justify-center py-20 text-center">
			<div class="text-3xl mb-2">🗓️</div>
			<div class="font-medium">{$i18n.t('Aucun événement à venir')}</div>
		</div>
	{:else}
		<div class="grid gap-2">
			{#each events as e (e.id)}
				<div class="flex items-center gap-3 px-4 py-3 rounded-2xl border border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850/40 transition">
					<div class="flex-1 min-w-0">
						<div class="text-sm font-medium truncate">{e.title}</div>
						<div class="text-[11px] text-gray-400 mt-0.5 flex flex-wrap gap-x-3">
							<span>🕑 {e.when_label}</span>
							{#if e.location}<span>📍 {e.location}</span>{/if}
						</div>
					</div>
					<Tooltip content={$i18n.t('Supprimer')}>
						<button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-red-500" on:click={() => confirmDelete(e)} aria-label="Supprimer">🗑</button>
					</Tooltip>
				</div>
			{/each}
		</div>
	{/if}
</div>
