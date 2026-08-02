<script lang="ts">
	// Le reste du catalogue Composio, dans une fenetre.
	//
	// Deroule dans la page, ce millier de cartes ecrasait la vitrine : on ne
	// voyait plus les vingt et une applications choisies. La fenetre garde la
	// page courte et donne au catalogue sa propre recherche, comme le fait deja
	// « Parcourir les integrations » pour les connecteurs natifs.
	import { createEventDispatcher, getContext } from 'svelte';

	import CarteApplication from './CarteApplication.svelte';
	import type { ApplicationAffichee } from '$lib/composio/etat';
	import { filtrer } from '$lib/composio/grouper';
	import { FAMILLES, estRecommandee } from '$lib/composio/catalogue';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let open = false;
	export let applications: ApplicationAffichee[] = [];

	let recherche = '';
	// Le reste du catalogue : sept cent cinquante micro-services d'API, montres
	// seulement a la demande. Rien n'est masque — c'est un clic de plus, et la
	// recherche les traverse de toute facon.
	let toutMontrer = false;

	$: autres = applications.filter((a) => !estRecommandee(a.slug));

	// Rangees par usage plutot que par ordre alphabetique : autrement
	// ActiveCampaign, Agentql et Ahrefs se suivent sans aucun rapport entre eux,
	// et l'oeil n'a aucun repere. Une famille vide n'est jamais rendue.
	$: parSlug = new Map(applications.map((a) => [`${a.slug}`.toLowerCase(), a]));
	$: sections = FAMILLES.map((famille) => ({
		...famille,
		contenu: famille.applications
			.map((slug) => parSlug.get(slug))
			.filter((a): a is ApplicationAffichee => a !== undefined)
	})).filter((famille) => famille.contenu.length > 0);
	// La recherche porte sur le catalogue ENTIER : ranger ne doit pas cacher.
	$: resultats = recherche.trim() ? filtrer(applications, recherche) : [];

	const fermer = () => {
		open = false;
		recherche = '';
		toutMontrer = false;
	};
</script>

{#if open}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click={fermer}
		role="presentation"
	>
		<!-- Le clic est arrete ici pour que cliquer DANS la fenetre ne la ferme pas.
		     Echap ferme aussi : sans clavier, une fenetre plein ecran piege
		     quiconque n'utilise pas la souris. -->
		<div
			class="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-2xl bg-white shadow-xl dark:bg-gray-900"
			on:click|stopPropagation
			on:keydown={(e) => e.key === 'Escape' && fermer()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<div class="border-b border-gray-200 px-5 pb-3 pt-5 dark:border-gray-800">
				<div class="flex items-center justify-between">
					<div class="text-base font-semibold">{$i18n.t('Parcourir les applications')}</div>
					<button
						class="rounded-lg p-1.5 text-gray-500 transition hover:bg-gray-100 dark:hover:bg-gray-800"
						on:click={fermer}
						aria-label={$i18n.t('Fermer')}
					>
						✕
					</button>
				</div>
			</div>

			<div class="flex-1 overflow-y-auto px-5 py-4">
				<input
					class="mb-4 w-full rounded-xl bg-gray-50 px-3 py-2 text-sm outline-none dark:bg-gray-850"
					type="search"
					placeholder={$i18n.t('Rechercher parmi {{count}} applications', {
						count: applications.length
					})}
					bind:value={recherche}
					autocomplete="off"
				/>

				{#if recherche.trim()}
					{#if resultats.length > 0}
						<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
							{#each resultats as application (application.slug)}
								<CarteApplication {application} on:changed={() => dispatch('changed')} />
							{/each}
						</div>
					{:else}
						<div class="py-10 text-center text-xs text-gray-500">
							{$i18n.t('Aucune application ne correspond à « {{terme}} ».', { terme: recherche })}
						</div>
					{/if}
				{:else}
					{#each sections as section, rang (section.id)}
						<section class="mb-7">
							<!-- Titre franc et separe : en gris leger et de la meme taille que
							     le reste, les familles se noyaient dans la grille et on ne
							     voyait plus ou l'une finissait et l'autre commencait. -->
							<h3
								class="mb-3 flex items-baseline gap-2 border-t border-gray-100 pt-4 text-[15px] font-semibold text-gray-900 dark:border-gray-800 dark:text-white {rang ===
								0
									? 'border-t-0 pt-0'
									: ''}"
							>
								{$i18n.t(section.libelle)}
								<span class="text-xs font-normal text-gray-400">
									{section.contenu.length}
								</span>
							</h3>
							<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
								{#each section.contenu as application (application.slug)}
									<CarteApplication {application} on:changed={() => dispatch('changed')} />
								{/each}
							</div>
						</section>
					{/each}

					{#if autres.length > 0}
						{#if toutMontrer}
							<h3 class="mb-2.5 mt-6 text-sm font-medium">
								{$i18n.t('Le reste du catalogue')}
								<span class="text-gray-400">({autres.length})</span>
							</h3>
							<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
								{#each autres as application (application.slug)}
									<CarteApplication {application} on:changed={() => dispatch('changed')} />
								{/each}
							</div>
						{:else}
							<!-- Rien n'est masque : ces sept cent cinquante entrees sont des
							     micro-services d'API sans usage pour une entreprise. Elles
							     restent a un clic, et la recherche les atteint deja. -->
							<button
								type="button"
								class="mt-6 w-full rounded-xl border border-dashed border-gray-200 py-3 text-sm text-gray-500 transition hover:border-gray-300 hover:text-gray-900 dark:border-gray-800 dark:hover:border-gray-700 dark:hover:text-white"
								on:click={() => (toutMontrer = true)}
							>
								+ {$i18n.t("d'intégrations")} ({autres.length})
							</button>
						{/if}
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/if}
