<script lang="ts">
	// Une application connectable : logo, nom, et un seul geste — « Connecter ».
	//
	// L'autorisation s'ouvre chez le fournisseur (Google, Microsoft...) dans une
	// fenetre a part, puis on interroge Composio jusqu'a ce que le compte soit
	// actif. Le client ne saisit aucune cle : c'est tout l'interet.
	import { createEventDispatcher, getContext, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';
	import ConnectorAboutModal from '$lib/components/connectors/ConnectorAboutModal.svelte';
	import { connecterApplication, retirerConnexion, suivreConnexion } from '$lib/apis/composio';
	import type { ApplicationAffichee } from '$lib/composio/etat';
	import { etatDeConnexion } from '$lib/composio/etat';
	import { nomAffiche } from '$lib/composio/categories';
	import { ficheDe } from '$lib/composio/fiches';
	import { descriptionFr } from '$lib/composio/descriptions';
	import { ficheCatalogueDe } from '$lib/composio/fiches-catalogue';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let application: ApplicationAffichee;

	// Nom lisible : le libelle francais quand il en existe un, sinon celui de
	// Composio (cf. categories.ts).
	$: nom = nomAffiche(application.slug, application.nom);
	$: initiales = nom
		.replace(/[^\p{L}\p{N}]/gu, '')
		.slice(0, 2)
		.toUpperCase();
	// Remis a zero quand la carte change d'application, sinon un logo casse
	// masquerait celui de la suivante.
	let logoCasse = false;
	$: if (application.slug) logoCasse = false;

	// Seules les applications de la vitrine ont une fiche redigee. Les mille du
	// reste du catalogue gardent une carte compacte : inventer leur description
	// serait faux, et en ecrire mille a la main serait obsolete dans six mois.
	$: fiche = ficheDe(application.slug);
	$: ficheCat = ficheCatalogueDe(application.slug);
	let aProposOuvert = false;

	// Hors vitrine, on n'invente rien : Composio decrit lui-meme chacune de ses
	// entrees. Sa phrase et son nombre d'actions valent mieux qu'une carte nue,
	// et restent justes quand son catalogue bouge. Ces textes sont en anglais —
	// les vingt-trois de la vitrine ont leur fiche francaise, qui passe devant.
	// Trois sources, dans cet ordre : la fiche redigee de la vitrine, le libelle
	// francais du catalogue recommande, puis le texte anglais de Composio pour le
	// fourre-tout. On ne descend d'un cran que faute de mieux.
	$: description =
		fiche?.desc ?? descriptionFr(application.slug) ?? application.description ?? null;
	$: etiquettes = fiche
		? fiche.tags
		: (ficheCat?.tags ?? [
				...(application.actions ? [$i18n.t('{{n}} actions', { n: application.actions })] : []),
				...(application.categories ?? []).slice(0, 2)
			]);
	// Il faut quelque chose a montrer : sans description ni site, la fenetre
	// n'apprendrait rien de plus que la carte.
	$: aProposPossible = Boolean(fiche || ficheCat || application.description || application.site);
	$: actionsAPropos = fiche
		? fiche.actions
		: (ficheCat?.actions ?? [
				// Le texte long de Composio a sa place ici, pas sur la carte.
				...(application.description ? [application.description] : []),
				...(application.actions
					? [$i18n.t('{{n}} actions disponibles pour l’assistant.', { n: application.actions })]
					: [])
			]);

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
				toast.success($i18n.t('{{name}} est connecté', { name: nom }));
				dispatch('changed');
				return;
			}
			if (lu === 'echouee') {
				connexion = false;
				toast.error($i18n.t('{{name}} n’a pas pu être connecté', { name: nom }));
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
			toast.success($i18n.t('{{name}} est déconnecté', { name: nom }));
			confirmationRetrait = false;
			dispatch('changed');
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			retrait = false;
		}
	};
</script>

<!-- `h-full` + grille : toutes les cartes d'une meme rangee prennent la hauteur
     de la plus haute. C'est ce qui les aligne, comme les cartes natives. -->
<div
	class="flex h-full flex-col gap-2.5 rounded-2xl border border-gray-100 p-4 card-lift hover:border-gray-200 dark:border-gray-850 dark:hover:border-gray-700"
>
	<div class="flex items-start gap-2.5">
		<div
			class="flex size-12 flex-none items-center justify-center overflow-hidden rounded-xl border border-gray-100 bg-white dark:border-gray-700"
		>
			{#if application.logo && !logoCasse}
				<img
					src={application.logo}
					alt={nom}
					class="max-h-full max-w-full object-contain"
					draggable="false"
					on:error={() => (logoCasse = true)}
				/>
			{:else}
				<!-- Repli sur les initiales : plusieurs logos du catalogue Composio
				     repondent sans image affichable, ce qui laissait un carre vide. -->
				<span class="text-xs font-medium text-gray-400">{initiales}</span>
			{/if}
		</div>

		<div class="flex min-w-0 flex-1 flex-col gap-1">
			<!-- Deux lignes plutot qu'une coupe seche : le catalogue compte une
			     quinzaine d'applications Google, toutes reduites a « Google … » sur
			     une seule ligne, donc impossibles a distinguer. -->
			<div class="text-sm font-medium leading-tight line-clamp-2 wrap-break-word" title={nom}>
				{nom}
			</div>
			{#if description}
				<div class="text-xs leading-snug text-gray-500 line-clamp-3">{description}</div>
			{/if}
		</div>

		{#if application.etat === 'connectee'}
			<span class="flex-none"><ActiveBadge /></span>
		{/if}
	</div>

	{#if etiquettes.length > 0}
		<!-- Trois etiquettes au plus : au-dela elles passent a la ligne et les
		     cartes cessent d'avoir la meme hauteur (verifie par fiches.test.ts). -->
		<div class="flex flex-wrap gap-1">
			{#each etiquettes.slice(0, 3) as tag (tag)}
				<span
					class="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-850 dark:text-gray-300"
				>
					{$i18n.t(tag)}
				</span>
			{/each}
		</div>
	{/if}

	{#if aProposPossible}
		<button
			type="button"
			class="self-start text-xs font-medium text-sky-600 hover:underline dark:text-sky-400"
			on:click={() => (aProposOuvert = true)}
		>
			{$i18n.t('Voir ce que ça fait')} ›
		</button>
	{/if}

	<div class="mt-auto flex items-center justify-between gap-2 pt-1">
		<span class="text-[11px] text-gray-500 dark:text-gray-400">
			{#if application.etat === 'connectee'}
				{$i18n.t('Connecté')}
			{:else if application.etat === 'en_cours'}
				{$i18n.t('Autorisation en cours…')}
			{:else if application.etat === 'echouee'}
				{$i18n.t('Connexion à refaire')}
			{:else}
				{$i18n.t('Connexion par compte')}
			{/if}
		</span>

		<div class="flex flex-none items-center gap-2">
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
</div>

{#if aProposPossible}
	<ConnectorAboutModal
		bind:open={aProposOuvert}
		name={nom}
		desc={description ?? ''}
		logoSrc={logoCasse ? '' : (application.logo ?? '')}
		actions={actionsAPropos}
		tags={etiquettes.slice(0, 3)}
	/>
{/if}
