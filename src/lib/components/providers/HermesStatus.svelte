<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getHermesStatus,
		checkHermesUpdate,
		startHermesUpdate,
		getHermesUpdateStatus
	} from '$lib/apis/providers';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let status: any = null;

	let checking = false;
	let checkOutput = '';

	let updateState: 'idle' | 'running' | 'success' | 'error' = 'idle';
	let updateLog = '';
	let poller: ReturnType<typeof setInterval> | null = null;

	const loadStatus = async () => {
		loading = true;
		try {
			status = await getHermesStatus(localStorage.token);
		} catch {
			toast.error($i18n.t('Impossible de récupérer l’état de Hermes'));
		} finally {
			loading = false;
		}
	};

	const check = async () => {
		checking = true;
		checkOutput = '';
		try {
			const r = await checkHermesUpdate(localStorage.token);
			checkOutput = r?.output ?? $i18n.t('Aucune information.');
		} catch {
			toast.error($i18n.t('Échec de la vérification'));
		} finally {
			checking = false;
		}
	};

	const stopPolling = () => {
		if (poller) {
			clearInterval(poller);
			poller = null;
		}
	};

	const pollUpdate = async () => {
		try {
			const st = await getHermesUpdateStatus(localStorage.token);
			updateLog = st?.log ?? updateLog;
			if (st && st.running === false && st.started) {
				stopPolling();
				if (st.success) {
					updateState = 'success';
					toast.success($i18n.t('Hermes mis à jour'));
					await loadStatus();
				} else {
					updateState = 'error';
					toast.error($i18n.t('Échec de la mise à jour'));
				}
			}
		} catch {
			stopPolling();
			updateState = 'error';
		}
	};

	const update = async () => {
		updateState = 'running';
		updateLog = '';
		try {
			await startHermesUpdate(localStorage.token);
			stopPolling();
			poller = setInterval(pollUpdate, 1500);
		} catch {
			updateState = 'error';
			toast.error($i18n.t('Impossible de démarrer la mise à jour'));
		}
	};

	onMount(loadStatus);
	onDestroy(stopPolling);
</script>

{#if loading}
	<div class="flex justify-center py-12"><Spinner className="size-6" /></div>
{:else if status}
	<!-- État -->
	<div class="p-4 rounded-2xl border border-gray-100 dark:border-gray-850 flex flex-col gap-2.5">
		<div class="text-sm font-medium mb-1">{$i18n.t('État de Hermes')}</div>

		<div class="flex items-center justify-between text-sm">
			<span class="text-gray-500">{$i18n.t('Version')}</span>
			<span class="font-medium text-right">{status.version ?? '—'}</span>
		</div>
		<div class="flex items-center justify-between text-sm">
			<span class="text-gray-500">{$i18n.t('Cerveau actif')}</span>
			<span class="font-medium text-right">
				{#if status.active}{status.active.provider_id} / {status.active.model_id}{:else}—{/if}
			</span>
		</div>
		<div class="flex items-center justify-between text-sm">
			<span class="text-gray-500">{$i18n.t('Moteur Hermes joignable')}</span>
			<span class="font-medium {status.hermes_available ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
				{status.hermes_available ? '✓' : '✗'}
			</span>
		</div>
		<div class="flex items-center justify-between text-sm">
			<span class="text-gray-500">{$i18n.t('Câble du chat (API :{port})').replace('{port}', status.api_server?.port ?? '')}</span>
			<span class="font-medium {status.api_server?.reachable ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
				{status.api_server?.reachable ? '✓' : '✗'}
			</span>
		</div>

		<div class="flex justify-end pt-1">
			<button
				type="button"
				class="text-xs px-3 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
				on:click={loadStatus}
			>
				{$i18n.t('Rafraîchir')}
			</button>
		</div>
	</div>

	<!-- Mise à jour -->
	<div class="mt-3 p-4 rounded-2xl border border-gray-100 dark:border-gray-850 flex flex-col gap-2.5">
		<div class="text-sm font-medium">{$i18n.t('Mise à jour de Hermes')}</div>
		<div class="text-xs text-gray-500">
			{$i18n.t('Récupère la dernière version de Hermes (et ses derniers modèles). Une sauvegarde est faite automatiquement avant.')}
		</div>

		<div class="flex items-center gap-2">
			<button
				type="button"
				class="text-sm px-3 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition disabled:opacity-50 inline-flex items-center gap-2"
				disabled={checking || updateState === 'running'}
				on:click={check}
			>
				{#if checking}<Spinner className="size-4" />{/if}
				{$i18n.t('Vérifier les mises à jour')}
			</button>
			<button
				type="button"
				class="text-sm px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-50 inline-flex items-center gap-2"
				disabled={updateState === 'running'}
				on:click={update}
			>
				{#if updateState === 'running'}<Spinner className="size-4" />{$i18n.t('Mise à jour en cours…')}{:else}{$i18n.t('Mettre à jour Hermes')}{/if}
			</button>
		</div>

		{#if checkOutput}
			<pre class="text-[11px] leading-relaxed bg-gray-50 dark:bg-gray-900 rounded-xl p-2 max-h-40 overflow-y-auto whitespace-pre-wrap">{checkOutput}</pre>
		{/if}

		{#if updateState === 'running'}
			<div class="text-xs text-amber-600 dark:text-amber-400">{$i18n.t('Mise à jour en cours, ne ferme pas la page…')}</div>
		{:else if updateState === 'success'}
			<div class="text-xs text-green-600 dark:text-green-400">{$i18n.t('Hermes est à jour ✓')}</div>
		{:else if updateState === 'error'}
			<div class="text-xs text-red-600 dark:text-red-400">{$i18n.t('La mise à jour a échoué. Vois le détail ci-dessous.')}</div>
		{/if}

		{#if updateLog}
			<pre class="text-[11px] leading-relaxed bg-gray-50 dark:bg-gray-900 rounded-xl p-2 max-h-60 overflow-y-auto whitespace-pre-wrap">{updateLog}</pre>
		{/if}
	</div>
{/if}
