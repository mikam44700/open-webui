<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	import { type Provider } from '$lib/utils/toolConnect';
	import ToolProviderCatalogCard from '$lib/components/integrations/ToolProviderCatalogCard.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Modale « Tout parcourir » de la page Recherche & web : recherche parmi TOUS les fournisseurs
	// (recherche web + navigateur + X), même esprit que « Parcourir les intégrations ».
	export let open = false;
	export let items: { toolsetName: string; provider: Provider }[] = [];

	let search = '';

	$: filtered = items.filter((it) => {
		if (!search.trim()) return true;
		const needle = search.trim().toLowerCase();
		return `${it.provider.name} ${it.provider.tag ?? ''}`.toLowerCase().includes(needle);
	});

	// Catégories = type d'outil (chaque carte porte son toolset d'origine). Libellés FR + ordre.
	const TOOLSET_LABEL: Record<string, string> = {
		web: 'Recherche web',
		browser: 'Navigateur automatisé',
		x_search: 'Recherche sur X'
	};
	const TOOLSET_ORDER = ['web', 'browser', 'x_search'];

	// Regroupe les fournisseurs filtrés par type d'outil, dans l'ordre voulu (inconnus à la fin).
	$: groups = (() => {
		const byToolset = new Map<string, { toolsetName: string; provider: Provider }[]>();
		for (const it of filtered) {
			if (!byToolset.has(it.toolsetName)) byToolset.set(it.toolsetName, []);
			byToolset.get(it.toolsetName)!.push(it);
		}
		const ordered: { key: string; label: string; items: typeof filtered }[] = [];
		for (const ts of TOOLSET_ORDER) {
			if (byToolset.has(ts)) {
				ordered.push({ key: ts, label: TOOLSET_LABEL[ts] ?? ts, items: byToolset.get(ts)! });
				byToolset.delete(ts);
			}
		}
		for (const [ts, list] of byToolset) {
			ordered.push({ key: ts, label: TOOLSET_LABEL[ts] ?? ts, items: list });
		}
		return ordered;
	})();

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
			<div class="px-5 pt-5 pb-3 border-b border-gray-200 dark:border-gray-800">
				<div class="flex items-center justify-between">
					<div class="text-base font-semibold">{$i18n.t('Parcourir les fournisseurs')}</div>
					<button
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500"
						on:click={close}
						aria-label={$i18n.t('Fermer')}
					>
						✕
					</button>
				</div>
			</div>

			<div class="flex-1 overflow-y-auto px-5 py-4">
				<input
					class="w-full px-3 py-2 text-sm rounded-xl bg-gray-50 dark:bg-gray-850 outline-none mb-4"
					placeholder={$i18n.t('Rechercher un fournisseur…')}
					bind:value={search}
				/>

				{#if filtered.length > 0}
					{#each groups as group (group.key)}
						<div class="mb-6 last:mb-0">
							<div
								class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2"
							>
								{$i18n.t(group.label)}
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
								{#each group.items as it (it.toolsetName + ':' + it.provider.name)}
									<ToolProviderCatalogCard
										toolsetName={it.toolsetName}
										provider={it.provider}
										on:changed={() => dispatch('changed')}
									/>
								{/each}
							</div>
						</div>
					{/each}
				{:else}
					<div class="text-xs text-gray-500 text-center py-10">
						{$i18n.t('Aucun fournisseur ne correspond.')}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
