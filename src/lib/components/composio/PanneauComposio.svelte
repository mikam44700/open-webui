<script lang="ts">
	// Assembleur court : il charge, il compose. Toute la derivation d'etat vit
	// dans lib/composio/etat.ts, avec ses tests a cote.
	//
	// Chaque source est chargee independamment : si le catalogue tombe, les
	// connexions deja etablies restent affichees, et inversement.
	import { getContext, onMount } from 'svelte';

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

	const i18n = getContext('i18n');

	// Les plus utiles a un dirigeant, remontees en tete du catalogue.
	const VEDETTES = ['gmail', 'googlecalendar', 'googledrive', 'outlook', 'onedrive', 'slack'];

	let chargement = true;
	let etat: EtatComposio | null = null;
	let applications: ApplicationComposio[] = [];
	let connexions: ConnexionComposio[] = [];
	let toutVoir = false;

	$: composees = composerApplications(applications, connexions);
	$: vedettes = composees.filter((a) => VEDETTES.includes(a.slug) || a.etat === 'connectee');
	$: affichees = toutVoir ? composees : vedettes;

	const charger = async () => {
		chargement = true;
		try {
			etat = await getEtatComposio(localStorage.token).catch(() => null);
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
		{#if affichees.length > 0}
			<div class="flex items-center justify-between">
				<div class="text-sm font-medium">
					{toutVoir ? $i18n.t('Toutes les applications') : $i18n.t('Vos applications')}
				</div>
				{#if composees.length > vedettes.length}
					<button
						type="button"
						class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white transition"
						on:click={() => (toutVoir = !toutVoir)}
					>
						{toutVoir
							? $i18n.t('Voir moins')
							: `${$i18n.t('Tout parcourir')} (${composees.length})`}
					</button>
				{/if}
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				{#each affichees as application (application.slug)}
					<CarteApplication {application} on:changed={charger} />
				{/each}
			</div>
		{:else}
			<div class="text-xs text-gray-500 text-center py-8">
				{$i18n.t('Aucune application disponible sur ce projet Composio.')}
			</div>
		{/if}
	{/if}
</div>
