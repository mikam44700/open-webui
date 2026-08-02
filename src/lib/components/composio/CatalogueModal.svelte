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

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let open = false;
	export let applications: ApplicationAffichee[] = [];

	let recherche = '';

	$: resultats = filtrer(applications, recherche);

	const fermer = () => {
		open = false;
		recherche = '';
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
			</div>
		</div>
	</div>
{/if}
