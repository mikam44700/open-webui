<script lang="ts">
	/**
	 * Une tuile de comptage de l'ecran d'accueil.
	 *
	 * Le ton ne se deduit pas du nombre : il vient de `lib/journal/synthese.ts`,
	 * parce que la regle qui le decide (l'attente n'est pas une panne, l'inconnu
	 * n'est pas un echec) est trop importante pour vivre dans un composant
	 * d'affichage, ou personne ne la testerait.
	 */
	import { getContext } from 'svelte';

	import type { StatutTraitement, Ton } from '$lib/journal/synthese';

	const i18n = getContext('i18n');

	export let statut: StatutTraitement;
	export let valeur: number;
	export let ton: Ton = 'neutre';

	const libelles: Record<StatutTraitement, string> = {
		ok: 'journal.statut.ok',
		pending: 'journal.statut.attente',
		error: 'journal.statut.erreur',
		unknown: 'journal.statut.inconnu'
	};

	const explications: Record<StatutTraitement, string> = {
		ok: 'journal.explication.ok',
		pending: 'journal.explication.attente',
		error: 'journal.explication.erreur',
		unknown: 'journal.explication.inconnu'
	};

	const couleurs: Record<Ton, string> = {
		neutre: 'text-gray-700 dark:text-gray-300',
		positif: 'text-emerald-600 dark:text-emerald-400',
		attention: 'text-amber-600 dark:text-amber-400',
		probleme: 'text-red-600 dark:text-red-400'
	};
</script>

<div
	class="flex flex-col gap-1 rounded-2xl border border-gray-100 bg-white p-4 dark:border-gray-850 dark:bg-gray-900"
>
	<div class="text-3xl font-semibold tabular-nums {couleurs[ton]}">
		{valeur}
	</div>
	<div class="text-sm font-medium text-gray-800 dark:text-gray-200">
		{$i18n.t(libelles[statut])}
	</div>
	<div class="text-xs text-gray-500 dark:text-gray-400">
		{$i18n.t(explications[statut])}
	</div>
</div>
