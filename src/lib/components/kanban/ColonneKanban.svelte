<script lang="ts">
	// Une colonne, dans le style de hermes-desktop : une voie delimitee et
	// pleine hauteur, en-tete a pastille de couleur, titre en majuscules et
	// compteur en pastille. La couleur fait le reperage — on trouve « Bloque »
	// sans lire les libelles.
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import CarteTache from './CarteTache.svelte';
	import type { TacheKanban } from '$lib/apis/kanban';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let libelle: string;
	export let taches: TacheKanban[] = [];
	/** Classe Tailwind ecrite en toutes lettres — voir COLONNES. */
	export let pastille = 'bg-gray-400';
</script>

<section
	class="flex w-72 flex-none flex-col overflow-hidden rounded-xl border border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900/40 sm:w-80"
>
	<header
		class="flex flex-none items-center justify-between border-b border-gray-200 px-3 py-2.5 dark:border-gray-800"
	>
		<div class="flex items-center gap-2">
			<span class="size-2 flex-none rounded-full {pastille}"></span>
			<h2 class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
				{$i18n.t(libelle)}
			</h2>
		</div>
		<span
			class="rounded-full bg-gray-200 px-1.5 py-px text-[11px] font-semibold text-gray-500 dark:bg-gray-800 dark:text-gray-400"
		>
			{taches.length}
		</span>
	</header>

	<div class="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-2">
		{#each taches as tache (tache.id)}
			<CarteTache {tache} on:ouvrir />
		{/each}

		{#if taches.length === 0}
			<!-- Un tiret, comme chez eux : la colonne est vide, ce n'est pas une
			     anomalie, ca ne merite pas une phrase. -->
			<p class="py-4 text-center text-xs text-gray-400 dark:text-gray-600">—</p>
		{/if}
	</div>
</section>
