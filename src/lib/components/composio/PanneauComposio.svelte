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
	import CatalogueModal from './CatalogueModal.svelte';
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
			{#if reste.length > 0}
				<!-- La porte vers le reste du catalogue tient sa PROPRE ligne, au-dessus
				     de la premiere section. Sur la ligne du titre, elle se confondait
				     avec le « Tout parcourir » des integrations natives, plus bas.
				     C'est aussi le SEUL endroit qui ouvre le catalogue : sans ce bouton,
				     le reste des applications devient inatteignable. -->
				<div class="flex justify-end">
					<button
						type="button"
						class="inline-flex items-center gap-1.5 rounded-xl border border-gray-100 px-3 py-1.5 text-sm text-gray-600 transition hover:border-gray-300 hover:text-gray-900 dark:border-gray-850 dark:text-gray-300 dark:hover:border-gray-700 dark:hover:text-white"
						on:click={() => (toutVoir = true)}
					>
						{`${$i18n.t('Tout parcourir')} (${reste.length})`}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
							/>
						</svg>
					</button>
				</div>
			{/if}

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
		{:else}
			<div class="py-8 text-center text-xs text-gray-500">
				{$i18n.t('Aucune application disponible sur ce projet Composio.')}
			</div>
		{/if}
	{/if}
</div>

<CatalogueModal bind:open={toutVoir} applications={reste} on:changed={charger} />
