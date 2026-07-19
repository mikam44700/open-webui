<script lang="ts">
	import { onMount } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		approveMemory,
		armGuardrails,
		getGuardrails,
		getPendingMemory,
		rejectMemory
	} from '$lib/apis/guardrails';

	// Panneau Garde-fous (chantier Guardrails, SPEC-guardrails.md) : l'état des
	// protections de la Boucle de confiance + la file d'approbation mémoire.
	let state = null; // { loop_breaker, memory_write_approval, pending_memory }
	let pending = null; // [{ id, summary, origin }]
	let erreur = '';
	let armement = false; // armement en cours
	let decisionEnCours = ''; // id de l'écriture en cours de traitement

	const charger = async () => {
		erreur = '';
		try {
			[state, pending] = await Promise.all([
				getGuardrails(localStorage.token),
				getPendingMemory(localStorage.token).then((r) => r?.pending ?? [])
			]);
		} catch (e) {
			erreur = typeof e === 'string' ? e : (e?.error?.message ?? 'Moteur indisponible.');
		}
	};

	const armer = async () => {
		armement = true;
		try {
			state = await armGuardrails(localStorage.token);
		} catch (e) {
			erreur = typeof e === 'string' ? e : (e?.error?.message ?? 'Armement impossible.');
		}
		armement = false;
	};

	const decider = async (id: string, decision: 'approve' | 'reject') => {
		decisionEnCours = id;
		try {
			if (decision === 'approve') await approveMemory(localStorage.token, id);
			else await rejectMemory(localStorage.token, id);
			await charger();
		} catch (e) {
			erreur = typeof e === 'string' ? e : (e?.error?.message ?? 'Décision impossible.');
		}
		decisionEnCours = '';
	};

	$: toutArme = state?.loop_breaker?.hard_stop_enabled && state?.memory_write_approval;

	onMount(charger);
</script>

<div class="px-3">
	{#if erreur}
		<div
			class="mb-4 rounded-2xl border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-sm text-red-700 dark:text-red-300"
		>
			{erreur}
			<button class="ml-2 underline" on:click={charger}>Réessayer</button>
		</div>
	{/if}

	{#if state === null && !erreur}
		<div class="flex justify-center py-16">
			<Spinner className="size-5" />
		</div>
	{:else if state}
		<!-- Les protections -->
		<div class="flex items-center justify-between mb-3">
			<div class="text-sm font-medium text-gray-700 dark:text-gray-300">Les protections</div>
			{#if !toutArme}
				<button
					class="inline-flex items-center gap-2 rounded-full bg-gray-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200 disabled:opacity-50"
					disabled={armement}
					on:click={armer}
				>
					{#if armement}<Spinner className="size-3.5" />{/if}
					Armer les protections
				</button>
			{/if}
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
			<!-- Disjoncteur de boucle -->
			<div
				class="flex flex-col rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-gray-900 p-5"
			>
				<div class="flex items-center justify-between">
					<div class="font-medium text-gray-900 dark:text-gray-50">⚡ Disjoncteur de boucle</div>
					{#if state.loop_breaker?.hard_stop_enabled}
						<span
							class="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
						>
							Actif
						</span>
					{:else}
						<span
							class="rounded-full bg-amber-100 dark:bg-amber-900/40 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300"
						>
							Inactif
						</span>
					{/if}
				</div>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1.5">
					Coupe automatiquement un agent qui tourne en rond : même erreur répétée, échecs en
					série ou travail qui ne progresse plus — la session s'arrête au lieu de consommer
					dans le vide.
				</p>
				{#if state.loop_breaker?.hard_stop_after && Object.keys(state.loop_breaker.hard_stop_after).length}
					<div class="mt-3 text-[11px] text-gray-400 dark:text-gray-500">
						Seuils de coupure : même erreur ×{state.loop_breaker.hard_stop_after.exact_failure ??
							5} · échecs du même outil ×{state.loop_breaker.hard_stop_after.same_tool_failure ??
							8} · sans progrès ×{state.loop_breaker.hard_stop_after.idempotent_no_progress ?? 5}
					</div>
				{/if}
			</div>

			<!-- Approbation mémoire -->
			<div
				class="flex flex-col rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-gray-900 p-5"
			>
				<div class="flex items-center justify-between">
					<div class="font-medium text-gray-900 dark:text-gray-50">🧠 Mémoire sous approbation</div>
					{#if state.memory_write_approval}
						<span
							class="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
						>
							Active
						</span>
					{:else}
						<span
							class="rounded-full bg-amber-100 dark:bg-amber-900/40 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300"
						>
							Inactive
						</span>
					{/if}
				</div>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1.5">
					Rien n'entre dans la mémoire de l'entreprise sans votre accord : chaque proposition de
					mémorisation attend votre validation ci-dessous. Un fait erroné ne peut jamais devenir
					« la vérité » en silence.
				</p>
			</div>
		</div>

		<!-- File d'approbation mémoire -->
		<div class="flex items-center justify-between mb-3">
			<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
				Écritures mémoire en attente
				{#if (pending ?? []).length}
					<span
						class="ml-1.5 rounded-full bg-amber-100 dark:bg-amber-900/40 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300"
					>
						{pending.length}
					</span>
				{/if}
			</div>
			<button
				class="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 underline"
				on:click={charger}
			>
				Actualiser
			</button>
		</div>

		{#if (pending ?? []).length === 0}
			<div
				class="rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 px-5 py-10 text-center"
			>
				<div class="font-medium text-gray-900 dark:text-gray-50">Aucune écriture en attente</div>
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					Quand un agent voudra mémoriser une information, elle apparaîtra ici — et rien ne
					s'écrira sans votre accord.
				</div>
			</div>
		{:else}
			<div class="flex flex-col gap-3 pb-6">
				{#each pending as item (item.id)}
					<div
						class="flex items-center justify-between gap-4 rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-gray-900 p-4"
					>
						<div class="min-w-0">
							<div class="text-sm text-gray-900 dark:text-gray-50">
								{item.summary || 'Écriture mémoire proposée'}
							</div>
							<div class="text-[11px] text-gray-400 dark:text-gray-500 mt-0.5">
								#{item.id}{item.origin === 'background_review' ? ' · proposée en tâche de fond' : ''}
							</div>
						</div>
						<div class="flex flex-none items-center gap-2">
							<button
								class="inline-flex items-center rounded-full bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:opacity-50"
								disabled={decisionEnCours === item.id}
								on:click={() => decider(item.id, 'approve')}
							>
								Approuver
							</button>
							<button
								class="inline-flex items-center rounded-full border border-gray-200 dark:border-gray-800 px-4 py-1.5 text-sm text-gray-700 dark:text-gray-300 transition hover:bg-gray-50 dark:hover:bg-gray-850 disabled:opacity-50"
								disabled={decisionEnCours === item.id}
								on:click={() => decider(item.id, 'reject')}
							>
								Rejeter
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<div class="pb-6 text-[11px] text-gray-400 dark:text-gray-500">
			Ces protections font partie de la Boucle de confiance LunarIA : elles sont armées
			automatiquement à chaque démarrage et tenues par le serveur — un agent ne peut ni les
			désactiver, ni s'auto-approuver.
		</div>
	{/if}
</div>
