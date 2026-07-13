<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let models: { id: string; label: string }[] = [];
	export let value: string = '';

	let search = '';

	// FR-012 : recherche/filtre sur les modèles
	$: filtered = search.trim()
		? models.filter(
				(m) =>
					m.label.toLowerCase().includes(search.toLowerCase()) ||
					m.id.toLowerCase().includes(search.toLowerCase())
			)
		: models;

	const choose = (id: string) => {
		value = id;
		dispatch('change', id);
	};
</script>

<div class="flex flex-col gap-2">
	<input
		class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
		placeholder={$i18n.t('Rechercher un modèle')}
		bind:value={search}
	/>

	<div class="max-h-60 overflow-y-auto flex flex-col gap-0.5 pr-1">
		{#if filtered.length === 0}
			<div class="text-xs text-gray-500 px-2 py-3 text-center">
				{$i18n.t('Aucun modèle trouvé')}
			</div>
		{:else}
			{#each filtered as model (model.id)}
				<button
					type="button"
					class="w-full flex items-center text-left text-sm px-3 py-2 rounded-xl transition
						{value === model.id
						? 'bg-gray-100 dark:bg-gray-850 font-medium'
						: 'hover:bg-gray-50 dark:hover:bg-gray-900'}"
					on:click={() => choose(model.id)}
				>
					<!-- overflow/ellipsis porté par le span (pas le bouton) + hauteur de ligne
					     garantie : le nom tient sur une ligne SANS jamais rogner les jambages. -->
					<span class="min-w-0 flex-1 truncate leading-normal py-px">{model.label}</span>
				</button>
			{/each}
		{/if}
	</div>
</div>
