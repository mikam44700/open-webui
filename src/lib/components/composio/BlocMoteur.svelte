<script lang="ts">
	// Deuxieme moitie du branchement : connecter Gmail chez Composio ne suffit pas,
	// encore faut-il que l'assistant sache s'en servir. Cela passe par un serveur
	// MCP distant declare dans le moteur.
	//
	// L'adresse MCP est donnee par Composio, dans le projet de ce client. Elle est
	// demandee ici plutot que devinee : une adresse inventee donnerait un serveur
	// injoignable, sans que la cause soit lisible.
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		brancherMoteur,
		debrancherMoteur,
		getBranchementMoteur,
		type BranchementMoteur
	} from '$lib/apis/composio';

	const i18n = getContext('i18n');

	let branchement: BranchementMoteur | null = null;
	let chargement = true;
	let occupe = false;
	let confirmationRetrait = false;

	const charger = async () => {
		chargement = true;
		branchement = await getBranchementMoteur(localStorage.token).catch(() => null);
		chargement = false;
	};

	const brancher = async () => {
		if (occupe) return;
		occupe = true;
		try {
			await brancherMoteur(localStorage.token);
			toast.success($i18n.t('Vos applications sont branchées sur l’assistant'));
			await charger();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			occupe = false;
		}
	};

	const debrancher = async () => {
		occupe = true;
		try {
			await debrancherMoteur(localStorage.token);
			toast.success($i18n.t('Applications débranchées de l’assistant'));
			confirmationRetrait = false;
			await charger();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			occupe = false;
		}
	};

	onMount(charger);
</script>

{#if chargement}
	<div class="flex justify-center py-4"><Spinner className="size-4" /></div>
{:else if branchement?.etat === 'injoignable'}
	<!-- Moteur muet n'est pas moteur en panne : on le dit sans alarmer. -->
	<div class="text-xs text-gray-500 text-pretty">
		{$i18n.t('Le moteur ne répond pas pour le moment. Le branchement se fera à son retour.')}
	</div>
{:else if branchement?.branche}
	<div class="flex items-center justify-between gap-3">
		<div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 min-w-0">
			<svg
				class="size-4 flex-none text-green-600 dark:text-green-500"
				viewBox="0 0 20 20"
				fill="currentColor"
				aria-hidden="true"
			>
				<path
					fill-rule="evenodd"
					d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 10.7a1 1 0 1 1 1.4-1.4l3.1 3.1 6.8-6.8a1 1 0 0 1 1.4 0Z"
					clip-rule="evenodd"
				/>
			</svg>
			<span class="truncate">
				{branchement.actif === false
					? $i18n.t('Branché sur l’assistant, mais éteint dans l’onglet MCP')
					: $i18n.t('Vos applications sont utilisables par l’assistant')}
			</span>
		</div>
		<div class="flex-none flex items-center gap-3">
			{#if confirmationRetrait}
				<button
					type="button"
					class="text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
					on:click={() => (confirmationRetrait = false)}
					disabled={occupe}
				>
					{$i18n.t('Annuler')}
				</button>
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 transition disabled:opacity-40"
					on:click={debrancher}
					disabled={occupe}
				>
					{#if occupe}<Spinner className="size-3.5" />{:else}{$i18n.t('Confirmer')}{/if}
				</button>
			{:else}
				<button
					type="button"
					class="text-xs text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition"
					on:click={() => (confirmationRetrait = true)}
				>
					{$i18n.t('Débrancher')}
				</button>
			{/if}
		</div>
	</div>
{:else}
	<div class="flex flex-col gap-2">
		<div class="text-xs text-gray-500 text-pretty">
			{$i18n.t(
				'Dernière étape : branchez ces applications sur l’assistant pour qu’il puisse s’en servir.'
			)}
		</div>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="flex-none text-xs px-3 py-1.5 rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
				disabled={occupe}
				on:click={brancher}
			>
				{#if occupe}<Spinner className="size-3.5" />{:else}{$i18n.t('Brancher')}{/if}
			</button>
		</div>
	</div>
{/if}
