<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CarteCapacite, { type Capacite } from './CarteCapacite.svelte';
	import {
		annulerOAuth,
		deconnecterOAuth,
		demarrerOAuth,
		getFournisseursCompte,
		soumettreOAuth,
		suivreOAuth
	} from '$lib/apis/hermes';

	type Compte = {
		id: string;
		titre: string;
		flow: string;
		connecte: boolean;
		detail?: string;
		docs?: string;
		commande?: string;
		deconnectable: boolean;
	};

	let chargement = true;
	let erreur = '';
	let comptes: Compte[] = [];
	let selection: Compte | null = null;
	let showSelection = false;
	let aDeconnecter: Compte | null = null;
	let actionEnCours = false;
	let messageAction = '';
	let sessionId = '';
	let code = '';
	let codeUtilisateur = '';
	let urlConnexion = '';
	let minuterie: ReturnType<typeof setInterval> | null = null;

	const arreterSuivi = () => {
		if (minuterie) clearInterval(minuterie);
		minuterie = null;
	};

	const normaliser = (reponse: any): Compte[] =>
		(reponse?.providers ?? [])
			.map((provider: any) => ({
				id: `${provider.id ?? provider.slug ?? ''}`,
				titre: `${provider.name ?? provider.label ?? provider.id ?? ''}`,
				flow: `${provider.flow ?? 'external'}`,
				connecte: Boolean(provider.status?.logged_in ?? provider.logged_in),
				detail:
					provider.status?.source_label ||
					provider.status?.token_preview ||
					provider.disconnect_hint ||
					undefined,
				docs: provider.docs_url || undefined,
				commande: provider.cli_command || undefined,
				deconnectable: provider.disconnectable !== false
			}))
			.filter((compte: Compte) => compte.id);

	const charger = async () => {
		chargement = true;
		erreur = '';
		try {
			comptes = normaliser(await getFournisseursCompte(localStorage.token));
		} catch (err) {
			erreur = `${err}`;
		} finally {
			chargement = false;
		}
	};

	const fermer = async () => {
		arreterSuivi();
		if (sessionId) {
			await annulerOAuth(localStorage.token, sessionId).catch(() => null);
		}
		selection = null;
		showSelection = false;
		sessionId = '';
		code = '';
		codeUtilisateur = '';
		urlConnexion = '';
		messageAction = '';
	};

	const resultatConnexion = async (resultat: any) => {
		sessionId = `${resultat?.session_id ?? resultat?.id ?? ''}`;
		codeUtilisateur = `${resultat?.user_code ?? resultat?.device_code ?? ''}`;
		// `verification_url` est le nom qu'emploie Hermes pour le flux « device
		// code » (OpenAI Codex, Nous). Il manquait ici : l'URL restait vide, la
		// fenetre d'autorisation ne s'ouvrait jamais et la connexion tournait
		// indefiniment sur « Connexion en cours… ». Les autres noms couvrent les
		// variantes de la norme OAuth et restent acceptes.
		urlConnexion = `${
			resultat?.verification_uri_complete ??
			resultat?.verification_url ??
			resultat?.verification_uri ??
			resultat?.authorization_url ??
			resultat?.auth_url ??
			resultat?.url ??
			''
		}`;
		if (urlConnexion) window.open(urlConnexion, '_blank', 'noopener,noreferrer');
		if (sessionId) {
			arreterSuivi();
			minuterie = setInterval(verifierEtat, 2000);
		}
	};

	const connecter = async () => {
		if (!selection || actionEnCours) return;
		actionEnCours = true;
		messageAction = '';
		try {
			const resultat = await demarrerOAuth(localStorage.token, selection.id);
			await resultatConnexion(resultat);
			if (!sessionId && !urlConnexion) {
				messageAction =
					selection.commande ||
					'Ce fournisseur demande une connexion externe. Consultez sa documentation.';
			}
		} catch (err) {
			messageAction = `${err}`;
		} finally {
			actionEnCours = false;
		}
	};

	const soumettre = async () => {
		if (!selection || !code.trim() || actionEnCours) return;
		actionEnCours = true;
		messageAction = '';
		try {
			const resultat = await soumettreOAuth(localStorage.token, selection.id, {
				code: code.trim(),
				session_id: sessionId || undefined
			});
			await resultatConnexion(resultat);
			await verifierEtat();
		} catch (err) {
			messageAction = `${err}`;
		} finally {
			actionEnCours = false;
		}
	};

	async function verifierEtat() {
		if (!selection || !sessionId) return;
		try {
			const resultat = await suivreOAuth(localStorage.token, selection.id, sessionId);
			const statut = `${resultat?.status ?? ''}`.toLowerCase();
			if (['approved', 'connected', 'complete', 'completed', 'success'].includes(statut)) {
				arreterSuivi();
				toast.success(`${selection.titre} est connecté`);
				await fermer();
				await charger();
			} else if (['error', 'denied', 'expired', 'cancelled'].includes(statut)) {
				arreterSuivi();
				messageAction = resultat?.error_message || `Connexion ${statut}.`;
			}
		} catch (err) {
			arreterSuivi();
			messageAction = `${err}`;
		}
	}

	const deconnecter = async () => {
		if (!aDeconnecter) return;
		actionEnCours = true;
		try {
			await deconnecterOAuth(localStorage.token, aDeconnecter.id);
			toast.success(`${aDeconnecter.titre} est déconnecté`);
			aDeconnecter = null;
			selection = null;
			showSelection = false;
			await charger();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			actionEnCours = false;
		}
	};

	const enCapacite = (compte: Compte): Capacite => ({
		id: compte.id,
		titre: compte.titre,
		description:
			compte.flow === 'device_code'
				? 'Connexion sécurisée par code, sans partager votre mot de passe.'
				: compte.flow === 'pkce'
					? 'Connexion sécurisée dans le navigateur.'
					: 'Compte reconnu nativement par Hermes.',
		detail: compte.detail,
		connecte: compte.connecte
	});

	const ouvrir = (compte: Compte) => {
		selection = compte;
		showSelection = true;
	};

	$: connectes = comptes.filter((compte) => compte.connecte);
	$: disponibles = comptes.filter((compte) => !compte.connecte);

	onMount(charger);
	onDestroy(arreterSuivi);
</script>

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500">
		<Spinner className="size-4" /> Lecture des comptes…
	</div>
{:else if erreur}
	<div class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">{erreur}</div>
{:else if comptes.length === 0}
	<div class="rounded-2xl border border-dashed border-gray-300 px-5 py-14 text-center dark:border-gray-700">
		<p class="text-pretty text-sm text-gray-500">Aucun fournisseur à connexion par compte n’est proposé par Hermes.</p>
		<button type="button" class="mt-3 rounded-lg bg-gray-100 px-3 py-1.5 text-xs dark:bg-gray-850" on:click={charger}>Relire le moteur</button>
	</div>
{:else}
	{#if connectes.length}
		<section class="mb-7">
			<h3 class="mb-3 text-sm font-medium">Comptes connectés <span class="text-gray-400">({connectes.length})</span></h3>
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each connectes as compte (compte.id)}
					<CarteCapacite capacite={enCapacite(compte)} famille="modele" actionLabel="Gérer" on:action={() => ouvrir(compte)} />
				{/each}
			</div>
		</section>
	{/if}
	<section>
		<h3 class="mb-3 text-sm font-medium">{connectes.length ? 'À découvrir' : 'Connexion par compte'}</h3>
		<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
			{#each disponibles as compte (compte.id)}
				<CarteCapacite capacite={enCapacite(compte)} famille="modele" actionLabel="Se connecter" on:action={() => ouvrir(compte)} />
			{/each}
		</div>
	</section>
{/if}

<Modal bind:show={showSelection} size="sm">
	{#if selection}
		<div class="p-5">
			<div class="flex items-start justify-between gap-4">
				<div>
					<h2 class="text-balance text-lg font-semibold">{selection.titre}</h2>
					<p class="mt-1 text-pretty text-xs text-gray-500">
						{selection.connecte ? 'Ce compte est utilisé par Hermes.' : 'Connectez ce compte directement à Hermes.'}
					</p>
				</div>
				<button type="button" aria-label="Fermer" class="flex size-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850" on:click={fermer}>×</button>
			</div>

			{#if selection.connecte}
				<div class="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-3 text-sm text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300">
					<div class="font-medium">Compte connecté</div>
					{#if selection.detail}<div class="mt-1 text-xs opacity-80">{selection.detail}</div>{/if}
				</div>
				<div class="mt-5 flex justify-between">
					<button type="button" disabled={!selection.deconnectable} class="rounded-lg px-3 py-2 text-xs text-red-600 hover:bg-red-50 disabled:opacity-40 dark:text-red-400 dark:hover:bg-red-950/20" on:click={() => (aDeconnecter = selection)}>
						Déconnecter
					</button>
					<button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs dark:bg-gray-850" on:click={fermer}>Fermer</button>
				</div>
			{:else}
				{#if urlConnexion || codeUtilisateur}
					<div class="mt-5 rounded-xl border border-sky-200 bg-sky-50 px-3.5 py-3 text-sm text-sky-800 dark:border-sky-900/40 dark:bg-sky-950/20 dark:text-sky-300">
						<div class="font-medium">Autorisez la connexion dans la fenêtre ouverte</div>
						{#if codeUtilisateur}
							<div class="mt-2 text-xs">Code à saisir :</div>
							<div class="mt-1 font-mono text-lg font-semibold">{codeUtilisateur}</div>
						{/if}
						{#if urlConnexion}
							<a class="mt-2 inline-block text-xs underline" href={urlConnexion} target="_blank" rel="noreferrer">Rouvrir la page de connexion</a>
						{/if}
					</div>
				{/if}

				{#if selection.flow === 'pkce' && !sessionId}
					<label class="mt-5 block text-xs font-medium" for="code-oauth">Code d’autorisation</label>
					<input id="code-oauth" bind:value={code} class="mt-1.5 w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Coller le code reçu" />
				{/if}

				{#if messageAction}
					<div class="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-amber-300">{messageAction}</div>
				{/if}

				<div class="mt-5 flex justify-end gap-2">
					<button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs dark:bg-gray-850" on:click={fermer}>Annuler</button>
					{#if selection.flow === 'pkce' && code.trim()}
						<button type="button" disabled={actionEnCours} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900" on:click={soumettre}>
							{actionEnCours ? 'Connexion…' : 'Valider le code'}
						</button>
					{:else if !sessionId}
						<button type="button" disabled={actionEnCours} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900" on:click={connecter}>
							{actionEnCours ? 'Ouverture…' : 'Continuer'}
						</button>
					{:else}
						<button type="button" class="rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white dark:bg-white dark:text-gray-900" on:click={verifierEtat}>Vérifier maintenant</button>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</Modal>

<ConfirmDialog
	show={Boolean(aDeconnecter)}
	title="Déconnecter ce compte ?"
	message="Hermes ne pourra plus utiliser les modèles liés à ce compte."
	confirmLabel="Déconnecter"
	onConfirm={deconnecter}
	on:cancel={() => (aDeconnecter = null)}
/>
