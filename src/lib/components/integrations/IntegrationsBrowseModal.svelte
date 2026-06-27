<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	import { INTEGRATION_FR, INTEGRATION_CATEGORIES } from '$lib/utils/integrationLabels';
	import IntegrationCard from './IntegrationCard.svelte';
	import CatalogList from '$lib/components/connectors/CatalogList.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Modale « Parcourir les intégrations » (façon Base44) : deux onglets Apps / MCP,
	// recherche et filtre par catégorie. Pensée pour accueillir beaucoup d'intégrateurs.
	export let open = false;
	export let integrations: any[] = [];

	let tab: 'apps' | 'mcp' = 'apps';
	let search = '';
	let category = '';

	// Lien « Demander un connecteur » (placeholder : remplacer par la vraie adresse support).
	const SUPPORT_EMAIL = 'support@agent-os.app';
	const requestMailto =
		`mailto:${SUPPORT_EMAIL}?subject=` +
		encodeURIComponent('Demande de connecteur — Agent OS') +
		'&body=' +
		encodeURIComponent('Bonjour,\n\nJ’aimerais que vous ajoutiez le connecteur suivant :\n\n');

	$: filteredApps = integrations.filter((it) => {
		const fr = INTEGRATION_FR[it.id];
		if (category && fr?.category !== category) return false;
		if (search.trim()) {
			const needle = search.trim().toLowerCase();
			const hay = `${fr?.name ?? it.id} ${fr?.desc ?? ''}`.toLowerCase();
			if (!hay.includes(needle)) return false;
		}
		return true;
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
		<div
			class="w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl bg-white dark:bg-gray-900 shadow-xl"
			on:click|stopPropagation
			role="dialog"
			aria-modal="true"
		>
			<!-- En-tête + onglets -->
			<div class="px-5 pt-5">
				<div class="flex items-center justify-between">
					<div class="text-base font-semibold">{$i18n.t('Parcourir les intégrations')}</div>
					<button
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500"
						on:click={close}
						aria-label={$i18n.t('Fermer')}
					>
						✕
					</button>
				</div>
				<div class="mt-3 flex gap-5 border-b border-gray-200 dark:border-gray-800">
					{#each [{ k: 'apps', l: 'Apps' }, { k: 'mcp', l: 'MCP' }] as t}
						<button
							type="button"
							class="relative pb-2.5 text-sm transition {tab === t.k
								? 'font-medium text-gray-900 dark:text-white'
								: 'text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300'}"
							on:click={() => (tab = t.k)}
						>
							{$i18n.t(t.l)}
							{#if tab === t.k}
								<span
									class="absolute -bottom-px left-0 right-0 h-0.5 rounded-full bg-gray-900 dark:bg-white"
								></span>
							{/if}
						</button>
					{/each}
				</div>
			</div>

			<!-- Corps -->
			<div class="flex-1 overflow-y-auto px-5 py-4">
				{#if tab === 'apps'}
					<!-- filtres -->
					<div class="flex items-center gap-2 mb-4">
						<input
							class="flex-1 px-3 py-2 text-sm rounded-xl bg-gray-50 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('Rechercher une intégration…')}
							bind:value={search}
						/>
						<select
							class="px-3 py-2 text-sm rounded-xl bg-gray-50 dark:bg-gray-850 outline-none"
							bind:value={category}
						>
							<option value="">{$i18n.t('Toutes')}</option>
							{#each INTEGRATION_CATEGORIES as c}
								<option value={c}>{c}</option>
							{/each}
						</select>
					</div>

					{#if filteredApps.length > 0}
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
							{#each filteredApps as integration (integration.id)}
								<IntegrationCard {integration} on:changed={() => dispatch('changed')} />
							{/each}
						</div>
					{:else}
						<div class="text-xs text-gray-500 text-center py-10">
							{$i18n.t('Aucune intégration ne correspond.')}
						</div>
					{/if}
				{:else}
					<CatalogList on:changed={() => dispatch('changed')} />
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
