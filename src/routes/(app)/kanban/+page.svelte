<script lang="ts">
	/**
	 * La page Kanban.
	 *
	 * Le moteur tient un registre de taches durable ; cette page le rend visible.
	 * Elle assemble, elle ne decide pas : la repartition en colonnes vit dans
	 * lib/kanban/colonnes.ts et la lecture des etats dans lib/kanban/etat.ts,
	 * chacune avec ses tests.
	 *
	 * Deux sources, chargees independamment : la configuration (quels tableaux
	 * existent) et le tableau lui-meme. La panne de l'une n'empeche pas l'autre
	 * de s'afficher.
	 */
	import { getContext, onDestroy, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { goto } from '$app/navigation';
	import { showSidebar, user, mobile } from '$lib/stores';

	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import PageHeader from '$lib/components/common/PageHeader.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import BandeauEtat from '$lib/components/kanban/BandeauEtat.svelte';
	import ColonneKanban from '$lib/components/kanban/ColonneKanban.svelte';
	import FicheTache from '$lib/components/kanban/FicheTache.svelte';

	import { COLONNES, repartir } from '$lib/kanban/colonnes';
	import { alerteChapeau, lectureDepuisErreur, type Lecture } from '$lib/kanban/etat';
	import {
		getConfigKanban,
		getFicheKanban,
		getTableauKanban,
		type FicheKanban,
		type TacheKanban
	} from '$lib/apis/kanban';

	const i18n = getContext<Writable<i18nType>>('i18n');

	/** Le repartiteur du moteur tourne toutes les 60 s ; 5 s tient SC-003 sans etre bavard. */
	const PERIODE_MS = 5000;

	let chargement = true;
	let taches: TacheKanban[] = [];
	let tableaux: string[] = [];
	let tableauCourant: string | null = null;
	let inclureArchivees = false;

	let lectureConfig: Lecture = { etat: 'ok' };
	let lectureTableau: Lecture = { etat: 'ok' };

	let ficheOuverte: FicheKanban | null = null;
	let idOuvert: string | null = null;
	let chargementFiche = false;

	let minuteur: ReturnType<typeof setInterval> | null = null;

	$: alerte = alerteChapeau([lectureConfig, lectureTableau]);
	$: repartition = repartir(taches, { inclureArchivees });

	const chargerConfig = async () => {
		try {
			const config = await getConfigKanban(localStorage.token);
			tableaux = config.tableaux ?? [];
			if (!tableauCourant) tableauCourant = config.tableauCourant ?? null;
			lectureConfig = { etat: 'ok' };
		} catch (erreur) {
			lectureConfig = lectureDepuisErreur(erreur);
		}
	};

	const chargerTableau = async () => {
		try {
			const reponse = await getTableauKanban(localStorage.token, {
				tableau: tableauCourant,
				inclureArchivees
			});
			// On n'ecrase que ce qui a ete lu : une lecture ratee laisse en place la
			// precedente plutot que de vider l'ecran sur une coupure de trois secondes.
			taches = reponse.taches ?? [];
			lectureTableau = { etat: 'ok' };
		} catch (erreur) {
			lectureTableau = lectureDepuisErreur(erreur);
		}
	};

	/** Les deux sources partent ensemble : aucune n'attend l'autre. */
	const charger = async () => {
		await Promise.all([chargerConfig(), chargerTableau()]);
	};

	const ouvrirFiche = async (tache: TacheKanban) => {
		idOuvert = tache.id;
		chargementFiche = true;
		try {
			ficheOuverte = await getFicheKanban(localStorage.token, tache.id);
		} catch {
			ficheOuverte = null;
		} finally {
			chargementFiche = false;
		}
	};

	const fermerFiche = () => {
		idOuvert = null;
		ficheOuverte = null;
	};

	/**
	 * Un tour de sondage.
	 *
	 * La fiche ouverte n'est PAS rechargee ici : le client peut etre en train d'y
	 * ecrire, et lui reprendre son texte sous les doigts serait pire que de
	 * l'afficher legerement en retard (FR-011).
	 */
	const sonder = () => {
		if (document.visibilityState !== 'visible') return;
		chargerTableau();
	};

	const surVisibilite = () => {
		// L'onglet revient au premier plan : on rattrape tout de suite plutot que
		// d'attendre le prochain tour.
		if (document.visibilityState === 'visible') chargerTableau();
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			goto('/');
			return;
		}

		await charger();
		chargement = false;

		minuteur = setInterval(sonder, PERIODE_MS);
		document.addEventListener('visibilitychange', surVisibilite);
	});

	onDestroy(() => {
		if (minuteur) clearInterval(minuteur);
		if (typeof document !== 'undefined') {
			document.removeEventListener('visibilitychange', surVisibilite);
		}
	});
</script>

<svelte:head>
	<title>Kanban · LunarIA</title>
</svelte:head>

<div
	class="flex h-dvh max-h-[100dvh] w-full max-w-full flex-col transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''}"
>
	<nav class="flex shrink-0 items-center px-3 pb-1 pt-2">
		{#if $mobile || !$showSidebar}
			<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
				<button
					class="flex cursor-pointer rounded-lg p-1.5 transition hover:bg-gray-100 dark:hover:bg-gray-850"
					on:click={() => showSidebar.set(!$showSidebar)}
					aria-label="Basculer la barre latérale"
				>
					<MenuLines />
				</button>
			</div>
		{/if}
	</nav>

	<div class="flex min-h-0 flex-1">
		<div class="flex min-w-0 flex-1 flex-col overflow-y-auto">
			<div class="mx-auto w-full max-w-7xl px-4 pb-10 pt-2 sm:px-6">
				<PageHeader
					eyebrow={$i18n.t('Kanban')}
					title={$i18n.t('Ce que votre assistant a sur le feu')}
					description={$i18n.t('Ce qui tourne, ce qui attend, et ce qui a besoin de vous.')}
				>
					<svelte:fragment slot="actions">
						<div class="flex flex-none items-center gap-3">
							{#if tableaux.length > 1}
								<select
									class="rounded-xl border border-gray-100 bg-transparent px-2 py-1 text-xs outline-none dark:border-gray-850"
									bind:value={tableauCourant}
									on:change={chargerTableau}
									aria-label={$i18n.t('Tableau')}
								>
									{#each tableaux as nom (nom)}
										<option value={nom}>{nom}</option>
									{/each}
								</select>
							{/if}

							<label
								class="flex cursor-pointer select-none items-center gap-2 text-xs text-gray-400 dark:text-gray-500"
							>
								<input type="checkbox" bind:checked={inclureArchivees} on:change={chargerTableau} />
								{$i18n.t('Archivées')}
							</label>

							<button
								type="button"
								class="rounded-xl border border-gray-100 px-2 py-1 text-xs text-gray-600 transition hover:border-gray-300 dark:border-gray-850 dark:text-gray-300"
								on:click={charger}
							>
								{$i18n.t('Actualiser')}
							</button>
						</div>
					</svelte:fragment>
				</PageHeader>

				<div class="mt-5">
					<BandeauEtat {alerte} onReessayer={charger} />

					{#if chargement}
						<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
					{:else if taches.length === 0 && lectureTableau.etat === 'ok'}
						<!-- Vide parce qu'il n'y a rien a faire, pas parce que quelque chose
						     est casse : le dire, plutot que d'aligner six colonnes vides. -->
						<div
							class="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-gray-200 py-16 text-center dark:border-gray-800"
						>
							<div class="text-sm font-medium">{$i18n.t('Aucune tâche en cours')}</div>
							<p class="max-w-md text-xs text-gray-500">
								{$i18n.t(
									'Votre assistant inscrit ici ce qu’il a à faire. Demandez-lui quelque chose et le tableau se remplira.'
								)}
							</p>
						</div>
					{:else}
						<!-- Seul le tableau defile horizontalement, jamais la page entiere. -->
						<div class="-mx-1 flex gap-4 overflow-x-auto px-1 pb-4">
							{#each COLONNES as colonne (colonne.cle)}
								<ColonneKanban
									libelle={colonne.cleI18n}
									taches={repartition.colonnes[colonne.cle]}
									sollicite={colonne.cle === 'bloque' || colonne.cle === 'avalider'}
									on:ouvrir={(e) => ouvrirFiche(e.detail)}
								/>
							{/each}
						</div>

						{#if repartition.inconnues.length > 0}
							<!-- Un etat que la page ne connait pas ne disparait pas : il se
							     montre a part, avec son nom. -->
							<div class="mt-4">
								<ColonneKanban
									libelle="États non reconnus"
									taches={repartition.inconnues}
									on:ouvrir={(e) => ouvrirFiche(e.detail)}
								/>
							</div>
						{/if}
					{/if}
				</div>
			</div>
		</div>

		{#if idOuvert}
			<FicheTache
				fiche={ficheOuverte}
				chargement={chargementFiche}
				on:fermer={fermerFiche}
				on:debloquee={() => {
					fermerFiche();
					chargerTableau();
				}}
				on:perime={() => {
					fermerFiche();
					chargerTableau();
				}}
			/>
		{/if}
	</div>
</div>
