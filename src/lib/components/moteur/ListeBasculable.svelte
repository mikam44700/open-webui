<script context="module" lang="ts">
	export type Element = {
		nom: string;
		titre: string;
		description?: string;
		actif: boolean;
		detail?: string;
	};
</script>

<script lang="ts">
	/**
	 * Liste d'elements activables — LunarIA V2.
	 *
	 * Sept onglets de la page Moteur affichent la meme chose : des cartes avec un
	 * logo, un nom, une description, un interrupteur. Ecrire sept fois ce
	 * composant, c'etait sept occasions de les laisser diverger. Il est donc
	 * unique et parametre.
	 *
	 * Mise en page reprise d'AgentOS V1 : ce qui est deja connecte remonte en
	 * haut, sous son propre titre. Le dirigeant qui ouvre la page cherche
	 * d'abord ce qu'il a, pas ce qu'il pourrait avoir.
	 */
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { urlLogo, logoBordABord, initiales, LOGO_PAR_DEFAUT } from './logos';

	export let elements: Element[] = [];
	export let chargement = false;
	export let erreur: string | null = null;
	/** Message affiche quand la liste est vide — different selon l'onglet. */
	export let messageVide = 'Rien à afficher pour le moment.';
	/** Laisse a false quand le moteur n'expose pas de bascule pour cette famille. */
	export let basculable = true;
	/** Titre de la section haute. « Connectés » pour des comptes, « Activés » pour des outils. */
	export let libelleConnectes = 'Activés';

	/** Remonte (nom, nouvelEtat) au parent, qui appelle le moteur. */
	export let onBascule: ((nom: string, actif: boolean) => void) | null = null;

	/** Noms en cours de bascule : evite le double-clic et montre l'attente. */
	export let enCours: Set<string> = new Set();

	$: connectes = elements.filter((e) => e.actif);
	$: aDecouvrir = elements.filter((e) => !e.actif);

	/**
	 * Un logo manquant ne doit pas laisser un carre casse : on bascule sur
	 * l'icone neutre, une seule fois, sans reboucler si elle manque aussi.
	 */
	const surErreurImage = (evenement: Event) => {
		const img = evenement.currentTarget as HTMLImageElement;
		if (img.src.endsWith('api.svg')) return;
		img.src = LOGO_PAR_DEFAUT;
	};
</script>

{#snippet carte(element: Element)}
	{@const logo = urlLogo(element.nom, element.titre)}
	<div
		class="card-lift flex items-start gap-3 rounded-2xl border border-gray-100 bg-white px-4 py-3.5 dark:border-gray-850 dark:bg-gray-900"
	>
		<!-- Pastille du logo : taille fixe pour que les cartes s'alignent, quel
		     que soit le rapport de forme de l'image. -->
		<div
			class="flex size-10 flex-none items-center justify-center overflow-hidden rounded-xl border border-gray-100 bg-white dark:border-gray-850 dark:bg-gray-850"
		>
			{#if logo}
				<img
					src={logo}
					alt=""
					draggable="false"
					on:error={surErreurImage}
					class="size-full {logoBordABord(element.nom, element.titre)
						? 'object-cover'
						: 'object-contain p-1.5'}"
				/>
			{:else}
				<span class="text-xs font-semibold text-gray-400 dark:text-gray-500">
					{initiales(element.titre)}
				</span>
			{/if}
		</div>

		<div class="min-w-0 flex-1">
			<div class="flex items-start justify-between gap-2">
				<div class="truncate text-sm font-medium text-gray-900 dark:text-gray-50">
					{element.titre}
				</div>

				<div class="flex-none pt-0.5">
					{#if basculable}
						{#if enCours.has(element.nom)}
							<Spinner className="size-4" />
						{:else}
							<Switch
								state={element.actif}
								on:change={() => onBascule?.(element.nom, !element.actif)}
							/>
						{/if}
					{:else if element.actif}
						<span
							class="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400"
						>
							<span class="size-1.5 rounded-full bg-emerald-500"></span>
							Connecté
						</span>
					{:else}
						<span class="text-xs text-gray-400 dark:text-gray-500">Non connecté</span>
					{/if}
				</div>
			</div>

			{#if element.description}
				<div class="mt-1 line-clamp-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">
					{element.description}
				</div>
			{/if}
			{#if element.detail}
				<div class="mt-1.5 text-[11px] text-gray-400 dark:text-gray-500">{element.detail}</div>
			{/if}
		</div>
	</div>
{/snippet}

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500 dark:text-gray-400">
		<Spinner className="size-4" />
		Lecture du moteur…
	</div>
{:else if erreur}
	<div
		class="rounded-2xl border border-red-200 bg-red-50 px-5 py-6 text-sm dark:border-red-900/40 dark:bg-red-950/20"
	>
		<div class="font-medium text-red-800 dark:text-red-300">Le moteur n'a pas répondu</div>
		<div class="mt-1 text-red-700/80 dark:text-red-400/80">{erreur}</div>
	</div>
{:else if elements.length === 0}
	<div
		class="rounded-2xl border border-dashed border-gray-300 px-5 py-16 text-center dark:border-gray-700"
	>
		<div class="text-sm text-gray-500 dark:text-gray-400">{messageVide}</div>
	</div>
{:else}
	{#if connectes.length > 0 && aDecouvrir.length > 0}
		<!-- Deux sections : ce qu'on a, puis ce qu'on pourrait avoir. Quand tout
		     est dans le meme etat, on n'affiche aucun titre — il n'apprendrait rien. -->
		<div class="mb-6">
			<div
				class="mb-2.5 px-0.5 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
			>
				{libelleConnectes}
				<span class="opacity-60">({connectes.length})</span>
			</div>
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each connectes as element (element.nom)}
					{@render carte(element)}
				{/each}
			</div>
		</div>

		<div>
			<div
				class="mb-2.5 px-0.5 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500"
			>
				À découvrir
				<span class="opacity-60">({aDecouvrir.length})</span>
			</div>
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each aDecouvrir as element (element.nom)}
					{@render carte(element)}
				{/each}
			</div>
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
			{#each elements as element (element.nom)}
				{@render carte(element)}
			{/each}
		</div>
	{/if}
{/if}
