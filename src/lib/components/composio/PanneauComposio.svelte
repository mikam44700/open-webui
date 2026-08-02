<script lang="ts">
	// Assembleur court : il charge, il compose. Toute la mise en ordre vit dans
	// lib/composio/grouper.ts et lib/composio/categories.ts, avec leurs tests.
	//
	// Chaque source est chargee independamment : si le catalogue tombe, les
	// connexions deja etablies restent affichees, et inversement.
	import { createEventDispatcher, getContext, onMount } from 'svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import BlocCle from './BlocCle.svelte';
	import BlocMoteur from './BlocMoteur.svelte';
	import CarteApplication from './CarteApplication.svelte';
	import {
		getApplicationsComposio,
		getConnexionsComposio,
		getEtatComposio,
		type ApplicationComposio,
		type ConnexionComposio,
		type EtatComposio
	} from '$lib/apis/composio';
	import { composerApplications } from '$lib/composio/etat';
	import { filtrer, grouper, horsCategories } from '$lib/composio/grouper';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	let chargement = true;
	let etat: EtatComposio | null = null;
	let applications: ApplicationComposio[] = [];
	let connexions: ConnexionComposio[] = [];
	let recherche = '';
	let toutVoir = false;

	$: composees = composerApplications(applications, connexions);
	$: sections = grouper(composees);
	$: reste = horsCategories(composees);
	// La recherche porte sur le catalogue ENTIER : ranger ne doit pas cacher.
	$: resultats = recherche.trim() ? filtrer(composees, recherche) : [];

	const charger = async () => {
		chargement = true;
		try {
			etat = await getEtatComposio(localStorage.token).catch(() => null);
			dispatch('etat', etat);
			if (!etat?.cle) {
				applications = [];
				connexions = [];
				return;
			}
			const [catalogue, comptes] = await Promise.all([
				getApplicationsComposio(localStorage.token).catch(() => null),
				getConnexionsComposio(localStorage.token).catch(() => null)
			]);
			applications = catalogue?.applications ?? [];
			connexions = comptes?.connexions ?? [];
		} finally {
			chargement = false;
		}
	};

	onMount(charger);
</script>

<div class="flex flex-col gap-4">
	<BlocCle {etat} on:changed={charger} />

	{#if etat?.cle && etat.etat === 'ok'}
		<!-- Le branchement moteur ne vaut que si la cle marche : sans elle, il n'y a
		     rien a brancher, et le proposer ne ferait qu'ajouter une etape morte. -->
		<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
			<BlocMoteur />
		</div>
	{/if}

	{#if chargement}
		<div class="flex justify-center py-10"><Spinner className="size-5" /></div>
	{:else if etat?.cle}
		{#if composees.length > 0}
			<div class="relative">
				<svg
					class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400"
					viewBox="0 0 20 20"
					fill="currentColor"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M9 3.5a5.5 5.5 0 1 0 3.4 9.9l3.6 3.6a1 1 0 0 0 1.4-1.4l-3.6-3.6A5.5 5.5 0 0 0 9 3.5Zm-3.5 5.5a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0Z"
						clip-rule="evenodd"
					/>
				</svg>
				<input
					class="w-full rounded-xl border border-gray-100 bg-transparent py-2.5 pl-9 pr-3 text-sm outline-none dark:border-gray-850"
					type="search"
					placeholder={$i18n.t('Rechercher parmi {{count}} applications', {
						count: composees.length
					})}
					bind:value={recherche}
					autocomplete="off"
				/>
			</div>
		{/if}

		{#if recherche.trim()}
			<!-- Recherche : une seule grille, tout le catalogue, sans sections. -->
			{#if resultats.length > 0}
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{#each resultats as application (application.slug)}
						<CarteApplication {application} on:changed={charger} />
					{/each}
				</div>
			{:else}
				<div class="py-8 text-center text-xs text-gray-500">
					{$i18n.t('Aucune application ne correspond à « {{terme}} ».', { terme: recherche })}
				</div>
			{/if}
		{:else if sections.length > 0 || reste.length > 0}
			{#each sections as section (section.id)}
				<section>
					<h3 class="mb-2.5 text-sm font-medium">
						{$i18n.t(section.libelle)}
						<span class="text-gray-400">({section.applications.length})</span>
					</h3>
					<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
						{#each section.applications as application (application.slug)}
							<CarteApplication {application} on:changed={charger} />
						{/each}
					</div>
				</section>
			{/each}

			{#if reste.length > 0}
				<!-- Le reste du catalogue n'est pas cache, il est range derriere une
				     porte : mille cartes en vrac ne servent personne. -->
				<div class="border-t border-gray-100 pt-4 dark:border-gray-850">
					{#if toutVoir}
						<div class="mb-2.5 flex items-center justify-between">
							<h3 class="text-sm font-medium">
								{$i18n.t('Le reste du catalogue')}
								<span class="text-gray-400">({reste.length})</span>
							</h3>
							<button
								type="button"
								class="text-sm text-gray-500 transition hover:text-gray-900 dark:hover:text-white"
								on:click={() => (toutVoir = false)}
							>
								{$i18n.t('Replier')}
							</button>
						</div>
						<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
							{#each reste as application (application.slug)}
								<CarteApplication {application} on:changed={charger} />
							{/each}
						</div>
					{:else}
						<button
							type="button"
							class="w-full rounded-xl border border-dashed border-gray-200 py-3 text-sm text-gray-500 transition hover:border-gray-300 hover:text-gray-900 dark:border-gray-800 dark:hover:border-gray-700 dark:hover:text-white"
							on:click={() => (toutVoir = true)}
						>
							{$i18n.t('Voir les {{count}} autres applications', { count: reste.length })}
						</button>
					{/if}
				</div>
			{/if}
		{:else}
			<div class="py-8 text-center text-xs text-gray-500">
				{$i18n.t('Aucune application disponible sur ce projet Composio.')}
			</div>
		{/if}
	{/if}
</div>
