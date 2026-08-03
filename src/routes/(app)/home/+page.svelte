<script lang="ts">
	/**
	 * Ecran d'accueil — ce que l'assistant a fait.
	 *
	 * C'est l'ecran qu'ouvre un dirigeant : il ne veut pas piloter le moteur, il
	 * veut savoir que ses commandes sont passees. Il repond a trois questions et
	 * s'arrete la — combien de traitements ont abouti, combien attendent une
	 * signature, combien ont echoue.
	 *
	 * Toute la logique de lecture vit dans `lib/journal/synthese.ts`, testee a
	 * cote. Ici, on charge et on compose.
	 */
	import { getContext, onMount } from 'svelte';

	import {
		getSyntheseJournal,
		getTraitements,
		type Fenetre,
		type SyntheseJournal,
		type Traitement
	} from '$lib/apis/journal';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import FileAttente from '$lib/components/journal/FileAttente.svelte';
	import ListeTraitements from '$lib/components/journal/ListeTraitements.svelte';
	import TuileCompteur from '$lib/components/journal/TuileCompteur.svelte';
	import { COMPTEURS_VIDES, alerteJournal, etatAffichage, tuiles } from '$lib/journal/synthese';

	const i18n = getContext('i18n');

	let synthese: SyntheseJournal | null = null;
	let enAttente: Traitement[] = [];
	let lectureEchouee = false;
	let chargement = true;
	let fenetre: Fenetre = 'jour';

	const fenetres: Fenetre[] = ['jour', 'semaine', 'mois'];

	const libellesFenetre: Record<Fenetre, string> = {
		jour: 'journal.fenetre.jour',
		semaine: 'journal.fenetre.semaine',
		mois: 'journal.fenetre.mois',
		tout: 'journal.fenetre.tout'
	};

	/**
	 * Les deux sources sont chargees separement, et une panne de l'une ne doit
	 * pas emporter l'autre : si la file a signer devient illisible, les
	 * compteurs restent affiches, et inversement.
	 */
	const charger = async (choix: Fenetre) => {
		chargement = true;
		lectureEchouee = false;

		const [resultatSynthese, resultatAttente] = await Promise.allSettled([
			getSyntheseJournal(localStorage.token, choix),
			getTraitements(localStorage.token, { statut: 'pending', limit: 20, fenetre: choix })
		]);

		if (resultatSynthese.status === 'fulfilled') {
			synthese = resultatSynthese.value;
		} else {
			// On ne remplace pas les donnees par des zeros : un journal illisible
			// n'est pas une journee sans travail.
			synthese = null;
			lectureEchouee = true;
			console.error(resultatSynthese.reason);
		}

		if (resultatAttente.status === 'fulfilled') {
			enAttente = resultatAttente.value;
		} else {
			enAttente = [];
			console.error(resultatAttente.reason);
		}

		chargement = false;
	};

	const changerFenetre = async (choix: Fenetre) => {
		fenetre = choix;
		await charger(choix);
	};

	onMount(() => charger(fenetre));

	$: compteurs = synthese?.compteurs ?? null;
	$: affichage = etatAffichage(compteurs, lectureEchouee);
	$: alerte = compteurs ? alerteJournal(compteurs) : null;
</script>

<svelte:head>
	<title>{$i18n.t('journal.titre')} · LunarIA</title>
</svelte:head>

<div class="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-6">
	<header class="flex flex-wrap items-end justify-between gap-3">
		<div>
			<h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('journal.titre')}
			</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('journal.sous_titre')}
			</p>
		</div>

		<div class="flex gap-1 rounded-xl bg-gray-50 p-1 dark:bg-gray-850">
			{#each fenetres as choix}
				<button
					type="button"
					class="rounded-lg px-3 py-1 text-sm transition {fenetre === choix
						? 'bg-white font-medium text-gray-900 shadow-sm dark:bg-gray-900 dark:text-gray-100'
						: 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'}"
					on:click={() => changerFenetre(choix)}
				>
					{$i18n.t(libellesFenetre[choix])}
				</button>
			{/each}
		</div>
	</header>

	{#if alerte}
		<div
			class="rounded-2xl border px-4 py-3 text-sm {alerte.gravite === 'avertissement'
				? 'border-red-200 bg-red-50 text-red-800 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300'
				: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-300'}"
		>
			{$i18n.t(alerte.cle)}
		</div>
	{/if}

	{#if chargement}
		<div class="flex justify-center py-12"><Spinner /></div>
	{:else if affichage === 'illisible'}
		<div
			class="rounded-2xl border border-gray-100 bg-white px-4 py-10 text-center dark:border-gray-850 dark:bg-gray-900"
		>
			<p class="text-sm text-gray-700 dark:text-gray-300">{$i18n.t('journal.illisible')}</p>
			<button
				type="button"
				class="mt-3 text-sm text-gray-600 underline dark:text-gray-400"
				on:click={() => charger(fenetre)}
			>
				{$i18n.t('journal.reessayer')}
			</button>
		</div>
	{:else}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			{#each tuiles(compteurs ?? COMPTEURS_VIDES) as tuile (tuile.statut)}
				<TuileCompteur statut={tuile.statut} valeur={tuile.valeur} ton={tuile.ton} />
			{/each}
		</div>

		<FileAttente traitements={enAttente} on:decide={() => charger(fenetre)} />

		<section class="flex flex-col gap-2">
			<h2 class="text-sm font-medium text-gray-800 dark:text-gray-200">
				{$i18n.t('journal.derniers')}
			</h2>

			{#if affichage === 'vide'}
				<p
					class="rounded-2xl border border-gray-100 bg-white px-4 py-10 text-center text-sm text-gray-500 dark:border-gray-850 dark:bg-gray-900 dark:text-gray-400"
				>
					{$i18n.t('journal.vide')}
				</p>
			{:else}
				<ListeTraitements traitements={synthese?.dernieres ?? []} />
			{/if}
		</section>
	{/if}
</div>
