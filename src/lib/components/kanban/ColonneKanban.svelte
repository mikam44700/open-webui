<script lang="ts">
	// Une colonne : son titre, son compte, sa pile de cartes.
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import CarteTache from './CarteTache.svelte';
	import type { TacheKanban } from '$lib/apis/kanban';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let libelle: string;
	export let taches: TacheKanban[] = [];
	/** Met la colonne en avant quand elle demande une action du client. */
	export let sollicite = false;
</script>

<section class="flex w-72 flex-none flex-col gap-2 sm:w-80">
	<header class="flex items-baseline gap-2 px-1">
		<h2
			class="text-sm font-semibold {sollicite
				? 'text-amber-700 dark:text-amber-300'
				: 'text-gray-900 dark:text-white'}"
		>
			{$i18n.t(libelle)}
		</h2>
		<span class="text-xs text-gray-400">{taches.length}</span>
	</header>

	<div class="flex flex-col gap-2">
		{#each taches as tache (tache.id)}
			<CarteTache {tache} on:ouvrir />
		{/each}

		{#if taches.length === 0}
			<!-- Une colonne vide le dit en une ligne discrete plutot que de laisser
			     un trou : le client doit savoir qu'il n'a rien rate. -->
			<p class="px-1 py-3 text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Rien ici.')}
			</p>
		{/if}
	</div>
</section>
