<script lang="ts">
	// Une tache, vue de loin. Style repris de hermes-desktop : fond franc sur la
	// voie plus sombre, titre lisible, age discret en bas a droite.
	//
	// Ce qui doit se lire sans ouvrir la fiche : le titre, ce que la tache
	// attend, et si elle tourne en rond. Le reste vit dans la fiche.
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { ageCourt, attendLeTemps, estInconnue, peutEtreDebloquee } from '$lib/kanban/colonnes';
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
	$: aVous = peutEtreDebloquee(tache);
	$: programmee = attendLeTemps(tache);
	$: inconnue = estInconnue(tache.statut);
	$: enCours = `${tache.statut}`.toLowerCase() === 'running';
	$: age = ageCourt(tache.ageSecondes);
	$: reblocages = tache.reblocages ?? 0;
	$: echecs = tache.echecsConsecutifs ?? 0;
	$: messages = tache.nombreMessages ?? 0;
</script>

<button
	type="button"
	class="flex w-full flex-col gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-left transition hover:border-gray-300 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700"
	on:click={() => dispatch('ouvrir', tache)}
>
	<div class="flex items-start gap-2">
		{#if enCours}
			<!-- La pastille qui bat : on voit d'un coup d'oeil ce qui travaille. -->
			<span class="mt-1 size-1.5 flex-none animate-pulse rounded-full bg-teal-500"></span>
		{/if}
		<span class="text-[13px] font-medium leading-snug text-gray-900 dark:text-white">
			{tache.titre}
		</span>
	</div>

	{#if aVous || motif || programmee || inconnue}
		<div class="flex flex-wrap items-center gap-1.5">
			{#if aVous}
				<!-- Le seul cas ou le client a quelque chose a faire : il doit sauter aux yeux. -->
				<span
					class="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
				>
					{$i18n.t(motif ?? 'Attend votre réponse')}
				</span>
			{:else if motif}
				<span
					class="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-600 dark:bg-gray-850 dark:text-gray-400"
				>
					{$i18n.t(motif)}
				</span>
			{/if}

			{#if programmee}
				<!-- Le moteur ne stocke aucune date de demarrage : on dit QUE la tache
				     attend, jamais QUAND elle repartira. -->
				<span
					class="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-600 dark:bg-gray-850 dark:text-gray-400"
				>
					{$i18n.t('Programmée')}
				</span>
			{/if}

			{#if inconnue}
				<!-- Un etat que la page ne connait pas reste visible et signale, jamais
				     range d'office : c'est le defaut qu'on corrige. -->
				<span
					class="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-600 dark:bg-gray-850 dark:text-gray-400"
				>
					{$i18n.t('État inconnu : {{statut}}', { statut: tache.statut })}
				</span>
			{/if}
		</div>
	{/if}

	<div class="flex items-center gap-2 text-[10px] text-gray-400 dark:text-gray-500">
		{#if tache.responsable}
			<span>{tache.responsable}</span>
		{/if}

		{#if messages > 0}
			<span>{$i18n.t('{{n}} messages', { n: messages })}</span>
		{/if}

		{#if reblocages > 1}
			<!-- Sans ca, le client debloque en boucle sans comprendre que le probleme
			     est ailleurs. -->
			<span class="text-amber-600 dark:text-amber-400">
				{$i18n.t('rebloquée {{n}} fois', { n: reblocages })}
			</span>
		{:else if echecs > 1}
			<span class="text-amber-600 dark:text-amber-400">
				{$i18n.t('{{n}} échecs de suite', { n: echecs })}
			</span>
		{/if}

		{#if age}
			<span class="ml-auto">{age}</span>
		{/if}
	</div>
</button>
