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
		placeholder={$i18n.t('Search a model')}
		bind:value={search}
	/>

	<div class="max-h-60 overflow-y-auto flex flex-col gap-0.5 pr-1">
		{#if filtered.length === 0}
			<div class="text-xs text-gray-500 px-2 py-3 text-center">
				{$i18n.t('No model found')}
			</div>
		{:else}
			{#each filtered as model (model.id)}
				<button
					type="button"
					class="text-left text-sm px-3 py-2 rounded-xl transition line-clamp-1
						{value === model.id
						? 'bg-gray-100 dark:bg-gray-850 font-medium'
						: 'hover:bg-gray-50 dark:hover:bg-gray-900'}"
					on:click={() => choose(model.id)}
				>
					{model.label}
				</button>
			{/each}
		{/if}
	</div>
</div>
