<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { expertMode } from '$lib/stores';
	import {
		getAutomations,
		pauseAutomation,
		resumeAutomation,
		runAutomation,
		deleteAutomation,
		type Automation
	} from '$lib/apis/automations-hermes';

	import AutomationHermesModal from './AutomationHermesModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { statusInfo } from '$lib/automations/labels';

	const i18n = getContext('i18n');

	let loading = true;
	let unavailable = false;
	let automations: Automation[] = [];

	let showModal = false;
	let editTarget: Automation | null = null;

	let showDeleteConfirm = false;
	let deleteTarget: Automation | null = null;

	const load = async () => {
		loading = true;
		unavailable = false;
		try {
			const res = await getAutomations(localStorage.token, $expertMode);
			automations = res?.automations ?? [];
		} catch (err) {
			unavailable = true;
		} finally {
			loading = false;
		}
	};

	const togglePause = async (a: Automation) => {
		try {
			const fn = a.status === 'paused' ? resumeAutomation : pauseAutomation;
			const res = await fn(localStorage.token, a.id);
			const updated = res?.automation;
			if (updated) automations = automations.map((x) => (x.id === a.id ? updated : x));
		} catch (err) {
			toast.error(typeof err === 'string' ? err : $i18n.t('Action impossible'));
		}
	};

	const runNow = async (a: Automation) => {
		try {
			const res = await runAutomation(localStorage.token, a.id);
			toast.success(res?.message ?? $i18n.t('Lancement programmé à l’instant'));
		} catch (err) {
			toast.error(typeof err === 'string' ? err : $i18n.t('Lancement impossible'));
		}
	};

	const confirmDelete = (a: Automation) => {
		deleteTarget = a;
		showDeleteConfirm = true;
	};

	const doDelete = async () => {
		if (!deleteTarget) return;
		try {
			await deleteAutomation(localStorage.token, deleteTarget.id);
			automations = automations.filter((x) => x.id !== deleteTarget!.id);
			toast.success($i18n.t('Automatisation supprimée'));
		} catch (err) {
			toast.error(typeof err === 'string' ? err : $i18n.t('Suppression impossible'));
		} finally {
			deleteTarget = null;
		}
	};

	const openCreate = () => {
		editTarget = null;
		showModal = true;
	};

	const openEdit = (a: Automation) => {
		editTarget = a;
		showModal = true;
	};

	onMount(load);
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Supprimer cette automatisation ?')}
	on:confirm={doDelete}
>
	<div class="text-sm text-gray-500">
		{$i18n.t('Cette automatisation ne sera plus exécutée.')}
		<span class="font-medium">{deleteTarget?.name}</span>
	</div>
</ConfirmDialog>

<AutomationHermesModal bind:show={showModal} automation={editTarget} on:save={load} />

<div class="flex flex-col w-full">
	<div class="flex justify-between items-center mb-4">
		<div>
			<div class="text-xl font-medium">{$i18n.t('Automatisations')}</div>
			<div class="text-xs text-gray-500">
				{$i18n.t('Vos tâches récurrentes, exécutées automatiquement par Agent OS.')}
			</div>
		</div>
		<button
			class="px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium"
			on:click={openCreate}
		>
			+ {$i18n.t('Nouvelle automatisation')}
		</button>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-20"><Spinner className="size-5" /></div>
	{:else if unavailable}
		<div class="flex flex-col items-center justify-center py-20 text-center">
			<div class="text-3xl mb-2">🔌</div>
			<div class="font-medium">{$i18n.t('Automatisations momentanément indisponibles')}</div>
			<div class="text-xs text-gray-500 mt-1">
				{$i18n.t('Le cerveau Agent OS ne répond pas pour l’instant. Réessayez dans un moment.')}
			</div>
			<button class="mt-3 text-sm underline" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else if automations.length === 0}
		<div class="flex flex-col items-center justify-center py-20 text-center">
			<div class="text-3xl mb-2">⚡</div>
			<div class="font-medium">{$i18n.t('Aucune automatisation pour l’instant')}</div>
			<div class="text-xs text-gray-500 mt-1">
				{$i18n.t('Créez une tâche qui s’exécute toute seule, par exemple « chaque matin, résume mes emails ».')}
			</div>
		</div>
	{:else}
		<div class="grid gap-2">
			{#each automations as a (a.id)}
				<div class="flex items-center gap-3 px-4 py-3 rounded-2xl border border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850/40 transition">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<span class="text-sm font-medium truncate">{a.name}</span>
							<span class="text-[10px] px-1.5 py-0.5 rounded-full {statusInfo(a.status).cls}">
								{$i18n.t(statusInfo(a.status).label)}
							</span>
						</div>
						<div class="text-xs text-gray-500 truncate">{a.instruction}</div>
						<div class="text-[11px] text-gray-400 mt-0.5 flex flex-wrap gap-x-3">
							<span>🕑 {a.rhythm_label}</span>
							{#if a.next_run_label}<span>{$i18n.t('prochaine')} : {a.next_run_label}</span>{/if}
							{#if a.status === 'error' && a.last_error_short}
								<span class="text-amber-600 dark:text-amber-400">⚠ {a.last_error_short}</span>
							{/if}
							{#if $expertMode && a.schedule_raw}
								<span class="font-mono text-gray-400">{a.schedule_raw}</span>
							{/if}
						</div>
					</div>

					<div class="flex items-center gap-1 shrink-0">
						<Tooltip content={$i18n.t('Lancer maintenant')}>
							<button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" on:click={() => runNow(a)} aria-label="Lancer">▶</button>
						</Tooltip>
						{#if a.status !== 'done'}
							<Tooltip content={a.status === 'paused' ? $i18n.t('Réactiver') : $i18n.t('Mettre en pause')}>
								<button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" on:click={() => togglePause(a)} aria-label="Pause/Reprise">
									{a.status === 'paused' ? '⏵' : '⏸'}
								</button>
							</Tooltip>
						{/if}
						<Tooltip content={$i18n.t('Modifier')}>
							<button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800" on:click={() => openEdit(a)} aria-label="Modifier">✎</button>
						</Tooltip>
						<Tooltip content={$i18n.t('Supprimer')}>
							<button class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-red-500" on:click={() => confirmDelete(a)} aria-label="Supprimer">🗑</button>
						</Tooltip>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
