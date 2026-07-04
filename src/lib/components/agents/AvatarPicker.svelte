<script lang="ts">
	// Galerie de sélection d'avatar (modale plein écran). Le dirigeant choisit la
	// « tête » de son agent parmi les 100 portraits maison. Recherche par prénom +
	// filtre Homme/Femme. Un clic sur une vignette sélectionne et ferme (1 clic).
	// La valeur échangée est le CHEMIN de l'image (ex. /assets/agents/mike.png),
	// directement utilisable comme src (même contrat que les templates).
	import { createEventDispatcher, getContext } from 'svelte';
	import { fade, fly } from 'svelte/transition';

	import { AVATARS, avatarImage, avatarId, type Gender } from './avatars';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let value: string | null = null; // chemin de l'avatar sélectionné
	// Identifiants d'avatars déjà pris par d'AUTRES agents (grisés, non sélectionnables).
	export let used: string[] = [];

	let query = '';
	let genderFilter: 'all' | Gender = 'all';

	// Normalise une chaîne pour une recherche insensible aux accents et à la casse.
	const norm = (s: string): string =>
		s
			.toLowerCase()
			.normalize('NFD')
			.replace(/[̀-ͯ]/g, '');

	$: q = norm(query.trim());
	$: filtered = AVATARS.filter(
		(a) =>
			(genderFilter === 'all' || a.gender === genderFilter) &&
			(!q || norm(a.label).includes(q) || a.id.includes(q))
	);

	const pick = (id: string) => {
		value = avatarImage(id);
		dispatch('change', value);
		close();
	};

	const close = () => {
		show = false;
		dispatch('close');
	};

	// Vignette actuellement sélectionnée (pour l'anneau de sélection).
	$: selectedId = avatarId(value);
	// Visages pris par un autre agent (le sien reste toujours disponible).
	$: usedSet = new Set(used.filter((id) => id !== selectedId));
</script>

{#if show}
	<div
		class="fixed inset-0 z-[10000] flex flex-col bg-white dark:bg-gray-900"
		transition:fade={{ duration: 150 }}
	>
		<!-- En-tête + recherche + filtre -->
		<div
			class="sticky top-0 z-10 bg-white/85 dark:bg-gray-900/85 backdrop-blur border-b border-gray-100 dark:border-gray-850"
		>
			<div class="max-w-3xl mx-auto px-5 py-4">
				<div class="flex items-center justify-between gap-3">
					<div class="text-base font-semibold tracking-tight">
						{$i18n.t('Choisissez son visage')}
					</div>
					<button
						class="size-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={close}
						aria-label={$i18n.t('Fermer')}>✕</button
					>
				</div>

				<div class="mt-3 flex flex-col sm:flex-row gap-2">
					<input
						bind:value={query}
						placeholder={$i18n.t('Rechercher un prénom…')}
						class="flex-1 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 rounded-xl px-3 py-2 outline-none focus:border-gray-300 dark:focus:border-gray-700 transition"
					/>
					<div class="flex items-center gap-1 rounded-xl bg-gray-100 dark:bg-gray-850 p-1">
						{#each [{ k: 'all', label: $i18n.t('Tous') }, { k: 'male', label: $i18n.t('Hommes') }, { k: 'female', label: $i18n.t('Femmes') }] as opt}
							<button
								class="text-xs font-medium px-3 py-1.5 rounded-lg transition {genderFilter === opt.k
									? 'bg-white dark:bg-gray-700 shadow-sm'
									: 'text-gray-500 hover:text-gray-800 dark:hover:text-gray-200'}"
								on:click={() => (genderFilter = opt.k as 'all' | Gender)}
							>
								{opt.label}
							</button>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<!-- Grille des vignettes -->
		<div class="flex-1 overflow-y-auto">
			<div class="max-w-3xl mx-auto px-5 py-5">
				{#if filtered.length === 0}
					<div class="text-center text-sm text-gray-500 py-16">
						{$i18n.t('Aucun avatar ne correspond à « {{q}} ».', { q: query })}
					</div>
				{:else}
					<div class="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-6 gap-3">
						{#each filtered as a (a.id)}
							{@const taken = usedSet.has(a.id)}
							<button
								class="group flex flex-col items-center gap-1.5 {taken
									? 'cursor-not-allowed'
									: ''}"
								on:click={() => (taken ? null : pick(a.id))}
								disabled={taken}
								aria-disabled={taken}
								title={taken ? $i18n.t('{{name}} — déjà utilisé', { name: a.label }) : a.label}
							>
								<div
									class="relative w-full aspect-square rounded-2xl overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-850 dark:to-gray-800 ring-2 transition {selectedId ===
									a.id
										? 'ring-black dark:ring-white'
										: taken
											? 'ring-transparent'
											: 'ring-transparent group-hover:ring-gray-300 dark:group-hover:ring-gray-600'}"
								>
									<img
										src={avatarImage(a.id)}
										alt={a.label}
										loading="lazy"
										class="absolute inset-0 size-full object-cover object-top transition {taken
											? 'grayscale opacity-40'
											: ''}"
									/>
									{#if selectedId === a.id}
										<span
											class="absolute top-1 right-1 size-5 rounded-full bg-black dark:bg-white text-white dark:text-black flex items-center justify-center text-[11px] shadow"
											>✓</span
										>
									{:else if taken}
										<span
											class="absolute inset-x-0 bottom-0 bg-black/55 text-white text-[9px] font-medium py-0.5 text-center"
											>{$i18n.t('déjà utilisé')}</span
										>
									{/if}
								</div>
								<span
									class="text-[11px] transition truncate max-w-full {taken
										? 'text-gray-400 dark:text-gray-600'
										: 'text-gray-500 group-hover:text-gray-800 dark:group-hover:text-gray-200'}"
									>{a.label}</span
								>
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
