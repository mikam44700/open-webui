<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { CONNECTOR_FR } from '$lib/utils/connectorLabels';
	import CatalogCard from './CatalogCard.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	// Modale « Parcourir les connecteurs MCP » (esprit identique à la modale Intégrations) :
	// recherche + grille du catalogue complet. Pensée pour accueillir beaucoup de connecteurs.
	export let open = false;
	export let entries: any[] = [];

	let search = '';

	// Lien « Demander un connecteur » (placeholder : remplacer par la vraie adresse support).
	const SUPPORT_EMAIL = 'support@agent-os.app';
	const requestMailto =
		`mailto:${SUPPORT_EMAIL}?subject=` +
		encodeURIComponent('Demande de connecteur MCP — Agent OS') +
		'&body=' +
		encodeURIComponent('Bonjour,\n\nJ’aimerais que vous ajoutiez le connecteur suivant :\n\n');

	$: filtered = entries.filter((e) => {
		if (!search.trim()) return true;
		const fr = CONNECTOR_FR[e.name];
		const needle = search.trim().toLowerCase();
		const hay = `${fr?.name ?? e.name} ${fr?.desc ?? e.description ?? ''}`.toLowerCase();
		return hay.includes(needle);
	});

	const close = () => {
		open = false;
	};
</script>

{#if open}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click={close}
		role="presentation"
	>
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl bg-white dark:bg-gray-900 shadow-xl"
			on:click|stopPropagation
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<!-- En-tête -->
			<div class="px-5 pt-5">
				<div class="flex items-center justify-between">
					<div class="text-base font-semibold">{$i18n.t('Parcourir les connecteurs MCP')}</div>
					<button
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500"
						on:click={close}
						aria-label={$i18n.t('Fermer')}
					>
						✕
					</button>
				</div>
				<div class="mt-3">
					<input
						class="w-full px-3 py-2 text-sm rounded-xl bg-gray-50 dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('Rechercher un connecteur…')}
						bind:value={search}
					/>
				</div>
			</div>

			<!-- Corps -->
			<div class="flex-1 overflow-y-auto px-5 py-4">
				{#if filtered.length > 0}
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
						{#each filtered as entry (entry.name)}
							<CatalogCard {entry} on:changed={() => dispatch('changed')} />
						{/each}
					</div>
				{:else}
					<div class="text-xs text-gray-500 text-center py-10">
						{$i18n.t('Aucun connecteur ne correspond.')}
					</div>
				{/if}
			</div>

			<!-- Footer épinglé : demander un connecteur (façon Base44). -->
			<div
				class="border-t border-gray-100 dark:border-gray-800 px-5 py-3 text-center text-sm text-gray-500"
			>
				{$i18n.t('Vous ne trouvez pas ce qu’il vous faut ?')}
				<a
					class="font-medium text-gray-900 underline underline-offset-2 hover:opacity-80 dark:text-white"
					href={requestMailto}
				>
					{$i18n.t('Demander un connecteur')}
				</a>
			</div>
		</div>
	</div>
{/if}
