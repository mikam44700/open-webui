<script lang="ts">
	// Bloc de tete de l'onglet Integrations : la ou se pose la cle Composio du client.
	//
	// La cle est propre a CE client (un projet Composio par client). Elle est posee
	// une fois a l'installation ; ensuite le bloc reste calme et le client ne voit
	// plus que ses applications, en dessous.
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		enregistrerCleComposio,
		retirerCleComposio,
		verifierCleComposio,
		type EtatComposio
	} from '$lib/apis/composio';
	import { cleAPoser, messageEtat } from '$lib/composio/etat';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let etat: EtatComposio | null = null;

	let valeur = '';
	let afficher = false;
	// Verrou partage : tester et enregistrer touchent la meme cle saisie. Sans lui,
	// un clic croise lance deux appels concurrents sur la meme valeur.
	let occupe = false;
	let test = false;
	let enregistrement = false;
	let confirmationRetrait = false;
	let retrait = false;

	$: aSaisir = cleAPoser(etat);
	$: message = messageEtat(etat);

	const tester = async () => {
		if (!valeur.trim() || occupe) return;
		occupe = true;
		test = true;
		try {
			const resultat = await verifierCleComposio(localStorage.token, valeur.trim());
			if (resultat?.valide) toast.success($i18n.t('Clé valide'));
			else toast.error(resultat?.motif || $i18n.t('Clé refusée par Composio'));
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			test = false;
			occupe = false;
		}
	};

	const enregistrer = async () => {
		if (!valeur.trim() || occupe) return;
		occupe = true;
		enregistrement = true;
		try {
			await enregistrerCleComposio(localStorage.token, valeur.trim());
			toast.success($i18n.t('Clé enregistrée — vos applications sont connectables'));
			valeur = '';
			dispatch('changed');
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			enregistrement = false;
			occupe = false;
		}
	};

	const retirer = async () => {
		retrait = true;
		try {
			await retirerCleComposio(localStorage.token);
			toast.success($i18n.t('Clé retirée'));
			confirmationRetrait = false;
			dispatch('changed');
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			retrait = false;
		}
	};
</script>

<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 flex flex-col gap-3">
	<div class="flex items-start justify-between gap-3">
		<div class="min-w-0">
			<div class="text-sm font-medium">Composio</div>
			<div class="text-xs text-gray-500 text-pretty">
				{$i18n.t('Connecte vos applications : messagerie, agenda, fichiers, CRM.')}
			</div>
		</div>
		{#if etat?.cle && etat.etat === 'ok'}
			<div class="flex-none flex items-center gap-1.5 text-xs text-green-600 dark:text-green-500">
				<svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
					<path
						fill-rule="evenodd"
						d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 10.7a1 1 0 1 1 1.4-1.4l3.1 3.1 6.8-6.8a1 1 0 0 1 1.4 0Z"
						clip-rule="evenodd"
					/>
				</svg>
				<span>{$i18n.t('Clé connectée')}</span>
			</div>
		{/if}
	</div>

	{#if message}
		<div
			class="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-300"
		>
			{message}
		</div>
	{/if}

	{#if aSaisir}
		<div class="flex items-center gap-2">
			<input
				class="flex-1 min-w-0 text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none"
				type={afficher ? 'text' : 'password'}
				placeholder={$i18n.t('Clé API Composio de ce client')}
				bind:value={valeur}
				autocomplete="off"
				on:keydown={(e) => e.key === 'Enter' && enregistrer()}
			/>
			{#if valeur}
				<button
					type="button"
					class="flex-none text-xs px-2 py-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => (afficher = !afficher)}
				>
					{afficher ? $i18n.t('Masquer') : $i18n.t('Afficher')}
				</button>
			{/if}
		</div>
		<div class="flex items-center justify-between gap-2">
			<span class="text-[11px] text-gray-400 text-pretty">
				{$i18n.t('Vos accès aux applications sont gardés par Composio, hébergé hors d’Europe.')}
			</span>
			<div class="flex-none flex items-center gap-2">
				<button
					type="button"
					class="text-xs px-2 py-1 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition disabled:opacity-40"
					disabled={!valeur.trim() || occupe}
					on:click={tester}
				>
					{#if test}<Spinner className="size-3.5" />{:else}{$i18n.t('Tester')}{/if}
				</button>
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
					disabled={!valeur.trim() || occupe}
					on:click={enregistrer}
				>
					{#if enregistrement}<Spinner className="size-3.5" />{:else}{$i18n.t('Enregistrer')}{/if}
				</button>
			</div>
		</div>
	{:else}
		<div class="flex items-center justify-end gap-3">
			{#if confirmationRetrait}
				<span class="text-xs text-gray-500 mr-auto text-pretty">
					{$i18n.t(
						'Retirer la clé ? Les applications déjà connectées restent chez Composio, mais ne seront plus joignables depuis cet écran.'
					)}
				</span>
				<button
					type="button"
					class="text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 transition"
					on:click={() => (confirmationRetrait = false)}
					disabled={retrait}
				>
					{$i18n.t('Annuler')}
				</button>
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 transition disabled:opacity-40"
					on:click={retirer}
					disabled={retrait}
				>
					{#if retrait}<Spinner className="size-3.5" />{:else}{$i18n.t('Confirmer')}{/if}
				</button>
			{:else}
				<button
					type="button"
					class="text-xs text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition"
					on:click={() => (confirmationRetrait = true)}
				>
					{$i18n.t('Retirer la clé')}
				</button>
			{/if}
		</div>
	{/if}
</div>
