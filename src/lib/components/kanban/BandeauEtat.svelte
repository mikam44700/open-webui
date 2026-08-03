<script lang="ts">
	// L'alerte chapeau, et rien d'autre.
	//
	// Regle D27 : une source injoignable n'est pas une panne, et un registre non
	// installe encore moins. D'ou deux tons distincts — une information pour ce
	// qui n'est pas installe, un avertissement pour ce qui ne repond pas — et
	// une seule alerte quel que soit le nombre de sources tombees.
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import type { Alerte } from '$lib/kanban/etat';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let alerte: Alerte | null = null;
	export let onReessayer: (() => void) | null = null;
</script>

{#if alerte}
	<div
		class="mb-5 flex items-start justify-between gap-3 rounded-2xl border px-4 py-3 text-sm {alerte.gravite ===
		'information'
			? 'border-gray-100 bg-gray-50 text-gray-700 dark:border-gray-850 dark:bg-gray-900/40 dark:text-gray-300'
			: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-200'}"
		role={alerte.gravite === 'information' ? 'note' : 'status'}
	>
		<div class="flex flex-col gap-1">
			<span class="text-pretty">{$i18n.t(alerte.cleI18n)}</span>

			{#if alerte.etat === 'absent'}
				<!-- Ce n'est pas une panne : on dit quoi faire, sans dramatiser. -->
				<span class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Installez-le sur le moteur pour voir apparaître le tableau ici.')}
				</span>
			{/if}
		</div>

		{#if onReessayer && alerte.etat !== 'absent'}
			<button
				type="button"
				class="flex-none rounded-lg px-2 py-1 text-xs font-medium underline hover:no-underline"
				on:click={onReessayer}
			>
				{$i18n.t('Réessayer')}
			</button>
		{/if}
	</div>
{/if}
