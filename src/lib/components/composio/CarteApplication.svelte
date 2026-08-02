<script lang="ts">
	// Une application connectable : logo, nom, et un seul geste — « Connecter ».
	//
	// L'autorisation s'ouvre chez le fournisseur (Google, Microsoft...) dans une
	// fenetre a part, puis on interroge Composio jusqu'a ce que le compte soit
	// actif. Le client ne saisit aucune cle : c'est tout l'interet.
	import { createEventDispatcher, getContext, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import { connecterApplication, retirerConnexion, suivreConnexion } from '$lib/apis/composio';
	import type { ApplicationAffichee } from '$lib/composio/etat';
	import { etatDeConnexion } from '$lib/composio/etat';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let application: ApplicationAffichee;

	let connexion = false;
	let confirmationRetrait = false;
	let retrait = false;
	let minuteur: ReturnType<typeof setTimeout> | null = null;

	// L'onglet peut se fermer pendant qu'une autorisation est en cours : sans cet
	// arret, le suivi continuerait a interroger Composio dans le vide.
	onDestroy(() => {
		if (minuteur) clearTimeout(minuteur);
	});

	const suivre = async (id: string, restant = 60) => {
		if (restant <= 0) {
			connexion = false;
			toast.error($i18n.t('Autorisation non terminée. Réessayez.'));
			return;
		}
		try {
			const etat = await suivreConnexion(localStorage.token, id);
			const lu = etatDeConnexion(etat?.etat ?? '');
			if (lu === 'connectee') {
				connexion = false;
				toast.success($i18n.t('{{name}} est connecté', { name: application.nom }));
				dispatch('changed');
				return;
			}
			if (lu === 'echouee') {
				connexion = false;
				toast.error($i18n.t('{{name}} n’a pas pu être connecté', { name: application.nom }));
				dispatch('changed');
				return;
			}
		} catch {
			// Un trou de reseau pendant l'autorisation n'est pas un echec : on
			// retente au tour suivant plutot que d'annoncer une panne.
		}
		minuteur = setTimeout(() => suivre(id, restant - 1), 2000);
	};

	const connecter = async () => {
		if (connexion) return;
		connexion = true;
		try {
			const resultat = await connecterApplication(
				localStorage.token,
				application.slug,
				`${window.location.origin}/hermes`
			);
			if (!resultat?.url) throw new Error($i18n.t('Adresse d’autorisation manquante.'));
			window.open(resultat.url, '_blank', 'noopener,width=520,height=680');
			if (resultat.id) suivre(resultat.id);
			else connexion = false;
		} catch (err) {
			connexion = false;
			toast.error(`${err}`);
		}
	};

	const retirer = async () => {
		if (!application.connexionId) return;
		retrait = true;
		try {
			await retirerConnexion(localStorage.token, application.connexionId);
			toast.success($i18n.t('{{name}} est déconnecté', { name: application.nom }));
			confirmationRetrait = false;
			dispatch('changed');
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			retrait = false;
		}
	};
</script>

<div
	class="flex items-center gap-3 p-3 rounded-2xl border border-gray-100 dark:border-gray-850 card-lift hover:border-gray-200 dark:hover:border-gray-700"
>
	<div
		class="flex-none size-10 rounded-xl border border-gray-100 dark:border-gray-700 bg-white overflow-hidden flex items-center justify-center"
	>
		{#if application.logo}
			<img
				src={application.logo}
				alt={application.nom}
				class="max-w-full max-h-full object-contain"
				draggable="false"
			/>
		{:else}
			<span class="text-xs font-medium text-gray-400">{application.nom.slice(0, 2)}</span>
		{/if}
	</div>

	<div class="flex-1 min-w-0">
		<div class="text-sm font-medium truncate">{application.nom}</div>
		{#if application.etat === 'connectee'}
			<div class="text-xs text-green-600 dark:text-green-500">{$i18n.t('Connecté')}</div>
		{:else if application.etat === 'en_cours'}
			<div class="text-xs text-gray-500">{$i18n.t('Autorisation en cours…')}</div>
		{:else if application.etat === 'echouee'}
			<div class="text-xs text-gray-500">{$i18n.t('Connexion à refaire')}</div>
		{/if}
	</div>

	<div class="flex-none flex items-center gap-2">
		{#if application.etat === 'connectee'}
			{#if confirmationRetrait}
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
					{$i18n.t('Déconnecter')}
				</button>
			{/if}
		{:else}
			<button
				type="button"
				class="text-xs px-3 py-1.5 rounded-lg btn-premium bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-40"
				on:click={connecter}
				disabled={connexion}
			>
				{#if connexion}<Spinner className="size-3.5" />{:else}{$i18n.t('Connecter')}{/if}
			</button>
		{/if}
	</div>
</div>
