<script lang="ts">
	// Bouton « Mettre à jour » réutilisable pour un outil installé en conteneur (SearXNG,
	// Crawl4AI). Même principe que la mise à jour du moteur Hermes : vérifie si une nouvelle
	// version (épinglée côté code) est disponible, et si oui propose un bouton qui lance la
	// MAJ en arrière-plan puis suit la progression par polling.
	//
	// Le bouton ne s'affiche QUE si une mise à jour est réellement disponible — sinon rien
	// (le dirigeant n'a aucune décision à prendre tant que tout est à jour).
	import { getContext, createEventDispatcher, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';

	// Fonctions API déjà liées au token (fournies par le parent).
	export let check: () => Promise<any>;
	export let start: () => Promise<any>;
	export let poll: () => Promise<any>;
	export let toolLabel = '';
	// Outil installé ? (inutile de vérifier une MAJ si l'outil n'est pas là.)
	export let enabled = true;

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	let available = false;
	let state: 'idle' | 'running' | 'error' = 'idle';
	let poller: ReturnType<typeof setInterval> | null = null;

	const stopPolling = () => {
		if (poller) {
			clearInterval(poller);
			poller = null;
		}
	};

	const checkNow = async () => {
		if (!enabled) {
			available = false;
			return;
		}
		try {
			const r = await check();
			available = !!r?.update_available;
		} catch {
			available = false;
		}
	};

	// Vérifie au montage et à chaque changement d'état d'installation.
	let lastEnabled: boolean | null = null;
	$: if (enabled !== lastEnabled) {
		lastEnabled = enabled;
		checkNow();
	}

	onDestroy(stopPolling);

	const tick = async () => {
		try {
			const st = await poll();
			if (st?.running) return; // toujours en cours
			stopPolling();
			if (st?.success) {
				state = 'idle';
				available = false;
				toast.success($i18n.t('{{tool}} est à jour.', { tool: toolLabel }));
				dispatch('updated');
			} else {
				state = 'error';
				toast.error($i18n.t('La mise à jour de {{tool}} a échoué.', { tool: toolLabel }));
			}
		} catch {
			// erreur réseau transitoire : on retente au prochain tick
		}
	};

	const update = async () => {
		state = 'running';
		try {
			await start();
			poller = setInterval(tick, 1500);
		} catch (err: any) {
			state = 'error';
			toast.error(
				typeof err === 'string'
					? err
					: (err?.error?.message ?? $i18n.t('Impossible de lancer la mise à jour.'))
			);
		}
	};
</script>

{#if state === 'running'}
	<span
		class="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 flex items-center gap-1.5"
		title={$i18n.t('Mise à jour en cours, ne ferme pas la page…')}
	>
		<Spinner className="size-3.5" />
		{$i18n.t('Mise à jour…')}
	</span>
{:else if available}
	<button
		type="button"
		class="text-xs px-3 py-1.5 rounded-lg border border-sky-300 dark:border-sky-700 text-sky-700 dark:text-sky-300 hover:bg-sky-50 dark:hover:bg-sky-950/40 transition"
		on:click={update}
	>
		{state === 'error' ? $i18n.t('Réessayer') : $i18n.t('Mettre à jour')}
	</button>
{/if}
