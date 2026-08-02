<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import CarteCapacite, { type Capacite } from './CarteCapacite.svelte';
	import type { FamilleLogo } from './logos';

	export let show = false;
	export let titre = 'Tout parcourir';
	export let elements: Capacite[] = [];
	export let famille: FamilleLogo = 'outil';
	export let actionLabel = 'Configurer';
	export let onAction: ((capacite: Capacite) => void) | null = null;

	let recherche = '';
	let categorie = 'Toutes';

	$: categories = [
		'Toutes',
		...Array.from(new Set(elements.map((element) => element.categorie).filter(Boolean) as string[]))
	];
	$: filtre = recherche.trim().toLocaleLowerCase('fr');
	$: visibles = elements.filter((element) => {
		const dansCategorie = categorie === 'Toutes' || element.categorie === categorie;
		const texte = `${element.titre} ${element.description ?? ''} ${element.id}`.toLocaleLowerCase(
			'fr'
		);
		return dansCategorie && (!filtre || texte.includes(filtre));
	});
</script>

<Modal bind:show size="xl">
	<div class="flex max-h-[85dvh] flex-col">
		<header class="flex items-start justify-between gap-4 border-b border-gray-100 px-5 py-4 dark:border-gray-850">
			<div>
				<h2 class="text-balance text-lg font-semibold text-gray-900 dark:text-white">{titre}</h2>
				<p class="mt-1 text-pretty text-xs text-gray-500 dark:text-gray-400">
					{elements.length} possibilités disponibles dans le moteur.
				</p>
			</div>
			<button
				type="button"
				class="flex size-8 items-center justify-center rounded-lg text-gray-400 transition-colors duration-150 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-850 dark:hover:text-gray-200"
				aria-label="Fermer le catalogue"
				on:click={() => (show = false)}
			>
				×
			</button>
		</header>

	<div class="border-b border-gray-100 px-5 py-3 dark:border-gray-850">
		<label class="sr-only" for="catalogue-recherche">Rechercher</label>
		<input
			id="catalogue-recherche"
			bind:value={recherche}
			type="search"
			placeholder="Rechercher une application, un fournisseur ou un outil…"
			class="w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm outline-hidden transition-colors duration-150 focus:border-gray-400 dark:border-gray-800 dark:bg-gray-900 dark:focus:border-gray-600"
		/>
		{#if categories.length > 2}
			<div class="mt-3 flex gap-1.5 overflow-x-auto pb-1">
				{#each categories as nom}
					<button
						type="button"
						class="whitespace-nowrap rounded-lg px-3 py-1.5 text-xs transition-colors duration-150 {categorie ===
						nom
							? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
							: 'bg-gray-50 text-gray-600 hover:bg-gray-100 dark:bg-gray-850 dark:text-gray-300 dark:hover:bg-gray-800'}"
						on:click={() => (categorie = nom)}
					>
						{nom}
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<div class="overflow-y-auto p-5">
		{#if visibles.length}
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each visibles as capacite (capacite.id)}
					<CarteCapacite
						{capacite}
						{famille}
						actionLabel={capacite.connecte || capacite.actif ? 'Gérer' : actionLabel}
						on:action={() => onAction?.(capacite)}
					/>
				{/each}
			</div>
		{:else}
			<div class="rounded-2xl border border-dashed border-gray-300 px-5 py-12 text-center dark:border-gray-700">
				<p class="text-sm text-gray-500 dark:text-gray-400">Aucun résultat pour cette recherche.</p>
				<button
					type="button"
					class="mt-3 rounded-lg bg-gray-100 px-3 py-1.5 text-xs text-gray-700 dark:bg-gray-850 dark:text-gray-200"
					on:click={() => {
						recherche = '';
						categorie = 'Toutes';
					}}
				>
					Effacer les filtres
				</button>
			</div>
		{/if}
	</div>
	</div>
</Modal>
