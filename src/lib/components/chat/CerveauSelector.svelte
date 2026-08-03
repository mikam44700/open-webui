<script lang="ts">
	/**
	 * Selecteur de cerveau — LunarIA V2.
	 *
	 * Remplace le selecteur de modele natif dans la barre du chat. Le natif ne
	 * peut annoncer qu'une ligne, `hermes-agent` : c'est tout ce que le moteur
	 * expose sur `/v1/models`. Le modele qui reflechit vraiment se choisit dans
	 * le moteur, et le champ `model` d'une requete de conversation est ignore.
	 *
	 * Deux consequences assumees, visibles a l'ecran :
	 *   - le choix est GLOBAL, pas par conversation : il vaut aussi pour les
	 *     conversations deja ouvertes. Le menu le dit.
	 *   - si le moteur ne repond pas, ce composant s'efface au lieu de mentir
	 *     (`indisponible`), et la barre retombe sur le selecteur natif.
	 */
	import { getContext, onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		getOptionsModeles,
		getFournisseursCompte,
		changerDeModele,
		getNiveauIntelligence,
		definirNiveauIntelligence
	} from '$lib/apis/hermes';
	import {
		cerveauActif,
		cerveauxDisponibles,
		comptesParFournisseur,
		estActif,
		listerCerveaux,
		type Cerveau,
		type CerveauActif
	} from '$lib/moteur/cerveaux';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	/**
	 * Niveaux d'intelligence, repris d'AgentOS V1 : le dirigeant choisit un
	 * comportement, pas une valeur d'effort de raisonnement.
	 */
	const NIVEAUX = [
		{ effort: 'low', label: 'Fast', description: 'Quick answers' },
		{ effort: 'medium', label: 'Balanced', description: 'The right trade-off' },
		{ effort: 'high', label: 'Thorough', description: 'Deeper thinking' },
		{ effort: 'xhigh', label: 'Maximum', description: 'Maximum reasoning' }
	];

	let show = false;
	let chargement = true;
	/** Le moteur n'a pas repondu : on s'efface, la barre reprend le selecteur natif. */
	let indisponible = false;

	let cerveaux: Cerveau[] = [];
	let actif: CerveauActif = { modele: null, fournisseur: null };
	/**
	 * Etat des comptes du moteur. Vide tant qu'il n'a pas repondu : rien n'est
	 * alors ecarte, on ne masque jamais sur une information qu'on n'a pas.
	 */
	let comptes: Record<string, boolean> = {};
	let effort = 'medium';
	let enCours: string | null = null;

	$: groupes = cerveauxDisponibles(cerveaux, actif, comptes);
	$: libelle = actif.modele ?? $i18n.t('Select a model');

	const charger = async () => {
		chargement = true;
		try {
			const reponse = await getOptionsModeles(localStorage.token);
			cerveaux = listerCerveaux(reponse);
			actif = cerveauActif(reponse);
			indisponible = false;
		} catch {
			// Moteur injoignable ou compte sans droit d'administration : le
			// selecteur se retire plutot que d'afficher une liste vide trompeuse.
			indisponible = true;
		} finally {
			chargement = false;
			dispatch('etat', { indisponible });
		}

		if (indisponible) return;

		// Les deux appels qui suivent affinent l'affichage sans jamais le bloquer :
		// chacun echoue seul, et le selecteur reste utilisable.
		try {
			comptes = comptesParFournisseur(await getFournisseursCompte(localStorage.token));
		} catch {
			// Sans cette liste, on ne sait pas distinguer un compte propre d'un
			// jeton emprunte : on montre tout plutot que d'ecarter au hasard.
		}

		try {
			effort = (await getNiveauIntelligence(localStorage.token))?.effort ?? 'medium';
		} catch {
			// Le niveau est un confort : son absence ne doit pas retirer le choix du modele.
		}
	};

	const choisir = async (cerveau: Cerveau) => {
		if (enCours || estActif(cerveau, actif)) return;
		enCours = cerveau.id;
		try {
			await changerDeModele(localStorage.token, cerveau.id, cerveau.fournisseur);
			actif = { modele: cerveau.id, fournisseur: cerveau.fournisseur ?? null };
			toast.success($i18n.t('The engine now thinks with {{model}}', { model: cerveau.titre }));
			show = false;
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			enCours = null;
		}
	};

	const choisirNiveau = async (niveau: string) => {
		if (effort === niveau) return;
		const precedent = effort;
		effort = niveau;
		try {
			await definirNiveauIntelligence(localStorage.token, niveau);
		} catch (err) {
			effort = precedent;
			toast.error(`${err}`);
		}
	};

	onMount(charger);
</script>

{#if !indisponible}
	<Dropdown bind:show align="start" sideOffset={4} contentClass="w-[22rem] max-w-[90vw]">
		<button
			type="button"
			id="cerveau-selector-button"
			class="flex min-w-0 max-w-full cursor-pointer items-center gap-1.5 rounded-lg px-2 py-1 text-[15px] font-normal text-gray-700 transition-colors duration-100 hover:bg-gray-50/40 dark:text-gray-200 dark:hover:bg-gray-800/40"
			aria-label={$i18n.t('Select a model')}
		>
			{#if chargement}
				<Spinner className="size-4" />
			{/if}
			<span class="truncate">{libelle}</span>
			<ChevronDown className="size-3 shrink-0 text-gray-400" strokeWidth="2.5" />
		</button>

		<div slot="content">
			<div
				class="rounded-2xl border border-gray-100 bg-white p-1 text-sm shadow-lg dark:border-gray-800 dark:bg-gray-900"
			>
				{#if groupes.length === 0}
					<div class="px-3 py-4 text-xs text-gray-500 dark:text-gray-400">
						{$i18n.t(
							'No provider is connected to the engine yet. Connect one from the Engine page.'
						)}
					</div>
				{:else}
					<div class="max-h-[min(24rem,60dvh)] overflow-y-auto overscroll-contain px-1 pt-1 pb-0.5">
						{#each groupes as groupe (groupe.fournisseur)}
							<div
								class="px-2 pt-2 pb-1 text-[11px] font-medium tracking-wide text-gray-400 uppercase dark:text-gray-500"
							>
								{groupe.nom}
							</div>

							{#each groupe.cerveaux as cerveau (cerveau.id)}
								{@const selectionne = estActif(cerveau, actif)}
								<button
									type="button"
									class="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-left transition hover:bg-gray-50 dark:hover:bg-gray-850 {selectionne
										? 'font-medium text-gray-900 dark:text-white'
										: 'text-gray-700 dark:text-gray-300'}"
									on:click={() => choisir(cerveau)}
								>
									<span class="min-w-0 flex-1 truncate">{cerveau.titre}</span>
									{#if enCours === cerveau.id}
										<Spinner className="size-3.5" />
									{:else if selectionne}
										<Check className="size-3.5" strokeWidth="2.5" />
									{/if}
								</button>
							{/each}
						{/each}
					</div>

					<div class="mt-1 border-t border-gray-100 px-1 pt-2 pb-1 dark:border-gray-800">
						<div
							class="px-2 pb-1 text-[11px] font-medium tracking-wide text-gray-400 uppercase dark:text-gray-500"
						>
							{$i18n.t('Thinking level')}
						</div>

						<div class="flex gap-1 px-1 pb-1">
							{#each NIVEAUX as niveau (niveau.effort)}
								<button
									type="button"
									title={$i18n.t(niveau.description)}
									class="flex-1 cursor-pointer rounded-lg px-1.5 py-1.5 text-[11px] transition {effort ===
									niveau.effort
										? 'bg-gray-900 font-medium text-white dark:bg-white dark:text-gray-900'
										: 'bg-gray-50 text-gray-600 hover:bg-gray-100 dark:bg-gray-850 dark:text-gray-300 dark:hover:bg-gray-800'}"
									on:click={() => choisirNiveau(niveau.effort)}
								>
									{$i18n.t(niveau.label)}
								</button>
							{/each}
						</div>
					</div>

					<div class="px-3 pt-1 pb-2 text-[11px] leading-snug text-gray-400 dark:text-gray-500">
						{$i18n.t('This choice applies to every conversation, including open ones.')}
					</div>
				{/if}
			</div>
		</div>
	</Dropdown>
{/if}
