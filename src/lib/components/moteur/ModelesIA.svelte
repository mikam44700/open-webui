<script lang="ts">
	/**
	 * Onglet « Modeles IA » — LunarIA V2.
	 *
	 * Le seul onglet ou l'on choisit au lieu d'activer : un modele est actif a la
	 * fois, c'est lui qui fait reflechir l'assistant. D'ou une liste a selection
	 * unique plutot que des interrupteurs.
	 */
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		getOptionsModeles,
		changerDeModele,
		getModelesCombines,
		type EtatMoteur
	} from '$lib/apis/hermes';
	import { expertMode } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import PanneauMoteur from './PanneauMoteur.svelte';
	import ListeBasculable from './ListeBasculable.svelte';
	import PanneauComptes from './PanneauComptes.svelte';
	import PanneauCles from './PanneauCles.svelte';
	import PanneauLocal from './PanneauLocal.svelte';
	import type { Element } from './ListeBasculable.svelte';
	import { enElements } from './normaliser';
	import { listerCerveaux, estActif as cerveauEstActif, type Cerveau } from '$lib/moteur/cerveaux';
	import { urlLogo, logoBordABord, initiales, LOGO_PAR_DEFAUT } from './logos';

	export let etat: EtatMoteur | null = null;

	/** Un logo manquant bascule sur l'icone neutre, sans reboucler si elle manque aussi. */
	const surErreurImage = (evenement: Event) => {
		const img = evenement.currentTarget as HTMLImageElement;
		if (img.src.endsWith('api.svg')) return;
		img.src = LOGO_PAR_DEFAUT;
	};

	/**
	 * Sous-onglets, portes de la V1.
	 *
	 * « Moteur » parle du moteur en tant que logiciel (version, mise a jour).
	 * Les autres rangent les fournisseurs par mode de connexion, exactement
	 * comme la V1 : par compte, par serveur local, ou combines.
	 *
	 * « Modèles IA combinés » est du reglage avance : on ne le montre qu'en
	 * Reglages avances, comme les onglets Garde-fous et Competences.
	 */
	const SOUS_ONGLETS = [
		{ cle: 'moteur', label: 'Moteur', expert: false },
		{ cle: 'modeles', label: 'Modèles', expert: false },
		{ cle: 'comptes', label: 'Comptes', expert: false },
		{ cle: 'cles', label: 'Clés API', expert: false },
		{ cle: 'local', label: 'Local', expert: false },
		{ cle: 'combines', label: 'Modèles IA combinés', expert: true }
	] as const;

	let sousOnglet: string = 'moteur';

	$: sousOngletsVisibles = SOUS_ONGLETS.filter((o) => $expertMode || !o.expert);
	// Reglages avances coupes sur un sous-onglet expert : on revient au premier.
	$: if (!$expertMode && SOUS_ONGLETS.find((o) => o.cle === sousOnglet)?.expert)
		sousOnglet = 'moteur';

	/** Panneaux secondaires : meme forme que ceux de la page, meme logique. */
	type Panneau = {
		elements: Element[];
		chargement: boolean;
		erreur: string | null;
		charge: boolean;
	};
	const vide = (): Panneau => ({ elements: [], chargement: false, erreur: null, charge: false });
	let secondaires: Record<string, Panneau> = {
		combines: vide()
	};

	const chargerSecondaire = async (cle: string, appel: () => Promise<any>) => {
		if (secondaires[cle].charge || secondaires[cle].chargement) return;
		secondaires[cle] = { ...secondaires[cle], chargement: true, erreur: null };
		try {
			secondaires[cle] = {
				elements: enElements(await appel()),
				chargement: false,
				erreur: null,
				charge: true
			};
		} catch (err) {
			secondaires[cle] = { elements: [], chargement: false, erreur: `${err}`, charge: true };
		}
	};

	$: {
		const t = () => localStorage.token;
		if (sousOnglet === 'combines') chargerSecondaire('combines', () => getModelesCombines(t()));
	}

	/**
	 * La mise a plat du catalogue vit dans `$lib/moteur/cerveaux` : le selecteur
	 * du chat lit le meme catalogue, et deux lectures divergentes finiraient par
	 * afficher deux verites differentes sur le modele actif.
	 */
	type Modele = Cerveau;

	let modeles: Modele[] = [];
	let chargement = true;
	let erreur: string | null = null;
	let enCours: string | null = null;
	/** Modele actif tel que le moteur le declare — fait foi sur l'API de conversation. */
	let actifModele: string | null = null;
	let actifFournisseur: string | null = null;

	const charger = async () => {
		chargement = true;
		erreur = null;
		try {
			const reponse = await getOptionsModeles(localStorage.token);
			modeles = listerCerveaux(reponse);
			// Le moteur declare lui-meme son couple actif : on le prend a la source
			// plutot que de le deduire, pour ne jamais afficher un « Actif » faux.
			actifModele = reponse?.model ?? etat?.modele_actif ?? null;
			actifFournisseur = reponse?.provider ?? etat?.fournisseur_actif ?? null;
		} catch (err) {
			erreur = `${err}`;
		} finally {
			chargement = false;
		}
	};

	/** Un modele n'est actif que si son nom ET son fournisseur correspondent. */
	const estActif = (modele: Modele) =>
		cerveauEstActif(modele, { modele: actifModele, fournisseur: actifFournisseur });

	const choisir = async (modele: Modele) => {
		if (enCours || estActif(modele)) return;
		enCours = modele.id;
		try {
			await changerDeModele(localStorage.token, modele.id, modele.fournisseur);
			actifModele = modele.id;
			actifFournisseur = modele.fournisseur ?? null;
			if (etat) etat = { ...etat, modele_actif: modele.id, fournisseur_actif: modele.fournisseur };
			toast.success(`Le moteur réfléchit maintenant avec ${modele.titre}`);
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			enCours = null;
		}
	};

	onMount(charger);
</script>

<!-- Sous-onglets en « puces », style repris d'AgentOS V1. Volontairement
     differents de la barre a pilule du haut : deux niveaux qui se ressemblent,
     on ne sait plus lequel commande quoi. -->
<div class="mb-4 flex flex-wrap gap-1.5">
	{#each sousOngletsVisibles as onglet}
		<button
			type="button"
			class="whitespace-nowrap rounded-lg px-3 py-1.5 text-xs transition {sousOnglet === onglet.cle
				? 'bg-gray-900 font-medium text-white dark:bg-white dark:text-gray-900'
				: 'bg-gray-50 text-gray-600 hover:bg-gray-100 dark:bg-gray-850 dark:text-gray-300 dark:hover:bg-gray-800'}"
			on:click={() => (sousOnglet = onglet.cle)}
		>
			{onglet.label}
		</button>
	{/each}
</div>

{#if sousOnglet === 'moteur'}
	<PanneauMoteur />
{:else if sousOnglet === 'comptes'}
	<PanneauComptes />
{:else if sousOnglet === 'cles'}
	<PanneauCles />
{:else if sousOnglet === 'local'}
	<PanneauLocal />
{:else if sousOnglet === 'combines'}
	<ListeBasculable
		elements={secondaires.combines.elements}
		chargement={secondaires.combines.chargement}
		erreur={secondaires.combines.erreur}
		basculable={false}
		messageVide="Aucun assemblage de modèles configuré."
	/>
{:else if chargement}
	<div
		class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500 dark:text-gray-400"
	>
		<Spinner className="size-4" />
		Lecture des modèles disponibles…
	</div>
{:else if erreur}
	<div
		class="rounded-2xl border border-red-200 bg-red-50 px-5 py-6 text-sm dark:border-red-900/40 dark:bg-red-950/20"
	>
		<div class="font-medium text-red-800 dark:text-red-300">Le moteur n'a pas répondu</div>
		<div class="mt-1 text-red-700/80 dark:text-red-400/80">{erreur}</div>
	</div>
{:else if modeles.length === 0}
	<div
		class="rounded-2xl border border-dashed border-gray-300 px-5 py-16 text-center dark:border-gray-700"
	>
		<div class="text-sm text-gray-500 dark:text-gray-400">
			Aucun modèle déclaré dans le moteur. Ajoutez une clé de fournisseur dans Hermes pour en voir
			apparaître ici.
		</div>
	</div>
{:else}
	<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
		{#each modeles as modele (`${modele.fournisseur ?? ''}/${modele.id}`)}
			{@const actif = estActif(modele)}
			{@const logo = urlLogo(modele.fournisseur, modele.nomFournisseur, modele.id)}
			<button
				type="button"
				class="card-lift flex items-start gap-3 rounded-2xl border px-4 py-3.5 text-left {actif
					? 'border-violet-300 bg-violet-50/60 dark:border-violet-800 dark:bg-violet-950/20'
					: 'border-gray-100 bg-white dark:border-gray-850 dark:bg-gray-900'}"
				on:click={() => choisir(modele)}
			>
				<div
					class="flex size-10 flex-none items-center justify-center overflow-hidden rounded-xl border border-gray-100 bg-white dark:border-gray-850 dark:bg-gray-850"
				>
					{#if logo}
						<img
							src={logo}
							alt=""
							draggable="false"
							on:error={surErreurImage}
							class="size-full {logoBordABord(modele.fournisseur, modele.nomFournisseur, modele.id)
								? 'object-cover'
								: 'object-contain p-1.5'}"
						/>
					{:else}
						<span class="text-xs font-semibold text-gray-400 dark:text-gray-500">
							{initiales(modele.titre)}
						</span>
					{/if}
				</div>

				<div class="min-w-0 flex-1">
					<div class="flex items-start justify-between gap-2">
						<div class="truncate text-sm font-medium text-gray-900 dark:text-gray-50">
							{modele.titre}
						</div>
						<div class="flex-none pt-0.5">
							{#if enCours === modele.id}
								<Spinner className="size-4" />
							{:else if actif}
								<span
									class="rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-medium text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
								>
									Actif
								</span>
							{/if}
						</div>
					</div>

					{#if modele.nomFournisseur ?? modele.fournisseur}
						<div
							class="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400"
						>
							{modele.nomFournisseur ?? modele.fournisseur}
							{#if modele.connecte === false}
								<span
									class="rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
								>
									clé manquante
								</span>
							{/if}
						</div>
					{/if}
				</div>
			</button>
		{/each}
	</div>
{/if}
