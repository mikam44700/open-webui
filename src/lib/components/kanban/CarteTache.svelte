<script lang="ts">
	// Une tache, vue de loin.
	//
	// Ce qui doit se lire sans ouvrir la fiche : le titre, ce que la tache
	// attend, et si elle tourne en rond. Le reste vit dans la fiche.
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { attendLeTemps, estInconnue, peutEtreDebloquee } from '$lib/kanban/colonnes';
	import type { TacheKanban } from '$lib/apis/kanban';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let tache: TacheKanban;

	// Le motif de blocage en clair. Le moteur en distingue quatre, et un seul
	// appelle une action du client — les libeller pareil reviendrait a lui dire
	// « occupe-toi de ca » sans lui dire quoi faire.
	const MOTIFS: Record<string, string> = {
		needs_input: 'Attend votre réponse',
		dependency: 'Attend une autre tâche',
		capability: 'Il manque un outil ou un accès',
		transient: 'Incident passager'
	};

	$: motif = tache.typeBlocage ? MOTIFS[`${tache.typeBlocage}`.toLowerCase()] : null;
	$: bloqueSansType = `${tache.statut}`.toLowerCase() === 'blocked' && !motif;
	$: aVous = peutEtreDebloquee(tache);
	$: programmee = attendLeTemps(tache);
	$: inconnue = estInconnue(tache.statut);
	$: reblocages = tache.reblocages ?? 0;
	$: echecs = tache.echecsConsecutifs ?? 0;
</script>

<button
	type="button"
	class="w-full rounded-xl border border-gray-100 bg-white px-3 py-2.5 text-left transition hover:border-gray-300 dark:border-gray-850 dark:bg-gray-900/40 dark:hover:border-gray-700"
	on:click={() => dispatch('ouvrir', tache)}
>
	<div class="text-sm font-medium leading-snug text-gray-900 dark:text-white">
		{tache.titre}
	</div>

	<div class="mt-1.5 flex flex-wrap items-center gap-1.5">
		{#if aVous}
			<!-- Le seul cas ou le client a quelque chose a faire : il doit sauter aux yeux. -->
			<span
				class="rounded-md bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
			>
				{$i18n.t(bloqueSansType ? 'Attend votre réponse' : (motif ?? 'Attend votre réponse'))}
			</span>
		{:else if motif}
			<span
				class="rounded-md bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-850 dark:text-gray-300"
			>
				{$i18n.t(motif)}
			</span>
		{/if}

		{#if programmee}
			<!-- Le moteur ne stocke aucune date de demarrage : on dit QUE la tache
			     attend, jamais QUAND elle repartira. -->
			<span
				class="rounded-md bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-850 dark:text-gray-300"
			>
				{$i18n.t('Programmée')}
			</span>
		{/if}

		{#if inconnue}
			<!-- Un etat que la page ne connait pas reste visible et signale, jamais
			     range d'office : c'est le defaut qu'on corrige. -->
			<span
				class="rounded-md bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-850 dark:text-gray-300"
			>
				{$i18n.t('État inconnu : {{statut}}', { statut: tache.statut })}
			</span>
		{/if}

		{#if tache.responsable}
			<span class="text-xs text-gray-500 dark:text-gray-400">{tache.responsable}</span>
		{/if}
	</div>

	{#if reblocages > 1 || echecs > 1}
		<!-- Sans ca, le client debloque en boucle sans comprendre que le probleme
		     est ailleurs. -->
		<div class="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
			{#if reblocages > 1}
				{$i18n.t('Débloquée {{n}} fois, puis rebloquée', { n: reblocages })}
			{:else}
				{$i18n.t('{{n}} échecs de suite', { n: echecs })}
			{/if}
		</div>
	{/if}
</button>
