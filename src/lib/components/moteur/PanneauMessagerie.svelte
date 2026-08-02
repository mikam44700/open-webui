<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { expertMode } from '$lib/stores';
	import CarteCapacite, { type Capacite } from './CarteCapacite.svelte';
	import {
		annulerJumelageMessagerie,
		appliquerJumelageMessagerie,
		configurerPlateformeMessagerie,
		demarrerJumelageMessagerie,
		getPlateformesMessagerie,
		suivreJumelageMessagerie,
		testerPlateformeMessagerie
	} from '$lib/apis/hermes';

	type Champ = {
		key: string;
		label: string;
		description?: string;
		required: boolean;
		isSet: boolean;
		secret: boolean;
	};

	type Plateforme = {
		id: string;
		titre: string;
		description: string;
		etat: string;
		connectee: boolean;
		active: boolean;
		configuree: boolean;
		disponible: boolean;
		experte: boolean;
		champs: Champ[];
	};

	let chargement = true;
	let erreur = '';
	let plateformes: Plateforme[] = [];
	let selection: Plateforme | null = null;
	let showSelection = false;
	let aDeconnecter: Plateforme | null = null;
	let valeurs: Record<string, string> = {};
	let effacees: string[] = [];
	let actionEnCours = false;
	let messageAction: { ok: boolean; texte: string } | null = null;
	let jumelageId = '';
	let jumelage: any = null;
	let minuterie: ReturnType<typeof setInterval> | null = null;

	const arreterSuivi = () => {
		if (minuterie) clearInterval(minuterie);
		minuterie = null;
	};

	const normaliser = (reponse: any): Plateforme[] =>
		(reponse?.platforms ?? [])
			.map((plateforme: any) => ({
				id: `${plateforme.id ?? plateforme.name ?? ''}`,
				titre: `${plateforme.name ?? plateforme.label ?? plateforme.id ?? ''}`,
				description:
					plateforme.description ||
					`Échangez avec LunarIA depuis ${plateforme.name ?? plateforme.id}.`,
				etat: `${plateforme.state ?? plateforme.status ?? ''}`,
				connectee:
					`${plateforme.state ?? plateforme.status ?? ''}` === 'connected' ||
					Boolean(plateforme.connected),
				active: Boolean(plateforme.enabled),
				configuree: Boolean(plateforme.configured),
				disponible: plateforme.available !== false,
				experte: Boolean(plateforme.expert_only),
				champs: (plateforme.env_vars ?? []).map((champ: any) => ({
					key: `${champ.key ?? champ.name ?? ''}`,
					label: `${champ.label ?? champ.name ?? champ.key ?? ''}`.replaceAll('_', ' '),
					description: champ.description,
					required: Boolean(champ.required),
					isSet: Boolean(champ.is_set),
					secret:
						champ.is_password !== false &&
						/(TOKEN|SECRET|PASSWORD|KEY)/.test(`${champ.key ?? champ.name ?? ''}`)
				}))
			}))
			.filter((plateforme: Plateforme) => plateforme.id);

	const charger = async () => {
		chargement = true;
		erreur = '';
		try {
			plateformes = normaliser(await getPlateformesMessagerie(localStorage.token));
		} catch (err) {
			erreur = `${err}`;
		} finally {
			chargement = false;
		}
	};

	const ouvrir = (plateforme: Plateforme) => {
		selection = plateforme;
		showSelection = true;
		valeurs = {};
		effacees = [];
		messageAction = null;
		jumelageId = '';
		jumelage = null;
	};

	const fermer = async () => {
		arreterSuivi();
		if (selection && jumelageId) {
			await annulerJumelageMessagerie(
				localStorage.token,
				selection.id,
				jumelageId
			).catch(() => null);
		}
		selection = null;
		showSelection = false;
		jumelageId = '';
		jumelage = null;
	};

	const enregistrer = async () => {
		if (!selection || actionEnCours) return;
		actionEnCours = true;
		messageAction = null;
		try {
			await configurerPlateformeMessagerie(localStorage.token, selection.id, {
				enabled: true,
				env: Object.fromEntries(
					Object.entries(valeurs).filter(([, valeur]) => valeur.trim()).map(([key, valeur]) => [key, valeur.trim()])
				),
				clear_env: effacees
			});
			const resultat = await testerPlateformeMessagerie(localStorage.token, selection.id);
			messageAction = {
				ok: Boolean(resultat?.ok),
				texte: resultat?.message || (resultat?.ok ? 'Connexion réussie.' : 'Configuration enregistrée, mais le test a échoué.')
			};
			await charger();
			const fraiche = plateformes.find((p) => p.id === selection?.id);
			if (fraiche) selection = fraiche;
			if (resultat?.ok) toast.success(`${selection.titre} est connecté`);
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			actionEnCours = false;
		}
	};

	const tester = async () => {
		if (!selection || actionEnCours) return;
		actionEnCours = true;
		messageAction = null;
		try {
			const resultat = await testerPlateformeMessagerie(localStorage.token, selection.id);
			messageAction = {
				ok: Boolean(resultat?.ok),
				texte: resultat?.message || (resultat?.ok ? 'Connexion réussie.' : 'Le canal ne répond pas.')
			};
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			actionEnCours = false;
		}
	};

	const deconnecter = async () => {
		if (!aDeconnecter) return;
		actionEnCours = true;
		try {
			await configurerPlateformeMessagerie(localStorage.token, aDeconnecter.id, {
				enabled: false,
				env: {},
				clear_env: aDeconnecter.champs.map((champ) => champ.key)
			});
			toast.success(`${aDeconnecter.titre} est déconnecté`);
			aDeconnecter = null;
			selection = null;
			await charger();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			actionEnCours = false;
		}
	};

	const commencerJumelage = async () => {
		if (!selection || actionEnCours) return;
		actionEnCours = true;
		messageAction = null;
		try {
			jumelage = await demarrerJumelageMessagerie(localStorage.token, selection.id);
			jumelageId = `${jumelage?.pairing_id ?? jumelage?.id ?? ''}`;
			if (!jumelageId) throw new Error('Hermes n’a pas renvoyé de session de jumelage.');
			arreterSuivi();
			minuterie = setInterval(suivreJumelage, 2000);
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			actionEnCours = false;
		}
	};

	async function suivreJumelage() {
		if (!selection || !jumelageId) return;
		try {
			jumelage = await suivreJumelageMessagerie(localStorage.token, selection.id, jumelageId);
			const statut = `${jumelage?.status ?? jumelage?.state ?? ''}`.toLowerCase();
			if (['ready', 'approved', 'connected', 'complete'].includes(statut)) {
				arreterSuivi();
				await appliquerJumelageMessagerie(localStorage.token, selection.id, jumelageId);
				toast.success(`${selection.titre} est jumelé`);
				jumelageId = '';
				await charger();
				await fermer();
			} else if (['error', 'denied', 'expired'].includes(statut)) {
				arreterSuivi();
				messageAction = { ok: false, texte: jumelage?.error || `Jumelage ${statut}.` };
			}
		} catch (err) {
			arreterSuivi();
			messageAction = { ok: false, texte: `${err}` };
		}
	}

	const enCapacite = (plateforme: Plateforme): Capacite => ({
		id: plateforme.id,
		titre: plateforme.titre,
		description: plateforme.description,
		detail: plateforme.connectee
			? 'Canal opérationnel'
			: plateforme.configuree
				? 'Configuré, en attente du moteur'
				: undefined,
		connecte: plateforme.connectee,
		disponible: plateforme.disponible
	});

	$: visibles = $expertMode
		? plateformes
		: plateformes.filter((plateforme) => plateforme.disponible && !plateforme.experte);
	$: connectees = visibles.filter((plateforme) => plateforme.connectee || plateforme.configuree);
	$: disponibles = visibles.filter((plateforme) => !plateforme.connectee && !plateforme.configuree);
	$: jumelagePossible = selection && ['telegram', 'whatsapp'].includes(selection.id);

	onMount(charger);
	onDestroy(arreterSuivi);
</script>

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500"><Spinner className="size-4" /> Lecture des canaux…</div>
{:else if erreur}
	<div class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">{erreur}</div>
{:else if visibles.length === 0}
	<div class="rounded-2xl border border-dashed border-gray-300 px-5 py-14 text-center dark:border-gray-700">
		<p class="text-pretty text-sm text-gray-500">Aucun canal n’est disponible dans ce mode.</p>
		<button type="button" class="mt-3 rounded-lg bg-gray-100 px-3 py-1.5 text-xs dark:bg-gray-850" on:click={() => expertMode.set(true)}>Afficher les canaux avancés</button>
	</div>
{:else}
	{#if connectees.length}
		<section class="mb-7">
			<h3 class="mb-3 text-sm font-medium">Canaux connectés <span class="text-gray-400">({connectees.length})</span></h3>
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each connectees as plateforme (plateforme.id)}
					<CarteCapacite capacite={enCapacite(plateforme)} famille="messagerie" actionLabel="Gérer" on:action={() => ouvrir(plateforme)} />
				{/each}
			</div>
		</section>
	{/if}
	<section>
		<h3 class="mb-3 text-sm font-medium">{connectees.length ? 'À découvrir' : 'Canaux disponibles'}</h3>
		<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
			{#each disponibles as plateforme (plateforme.id)}
				<CarteCapacite capacite={enCapacite(plateforme)} famille="messagerie" actionLabel="Configurer" on:action={() => ouvrir(plateforme)} />
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
					<p class="mt-1 text-pretty text-xs text-gray-500">{selection.description}</p>
				</div>
				<button type="button" aria-label="Fermer" class="flex size-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850" on:click={fermer}>×</button>
			</div>

			{#if jumelagePossible && !selection.connectee}
				<div class="mt-5 rounded-xl border border-sky-200 bg-sky-50 p-3.5 dark:border-sky-900/40 dark:bg-sky-950/20">
					<div class="text-sm font-medium text-sky-900 dark:text-sky-200">Connexion guidée</div>
					<p class="mt-1 text-pretty text-xs text-sky-700 dark:text-sky-300">Hermes ouvre un jumelage sécurisé sans afficher vos identifiants.</p>
					{#if jumelage}
						{#if jumelage.qr_code_data_url || jumelage.qr_data_url}
							<img src={jumelage.qr_code_data_url || jumelage.qr_data_url} alt="Code QR de jumelage" class="mx-auto mt-3 size-48 rounded-xl bg-white p-2" />
						{/if}
						{#if jumelage.user_code || jumelage.code}
							<div class="mt-3 text-center font-mono text-lg font-semibold">{jumelage.user_code || jumelage.code}</div>
						{/if}
						<p class="mt-2 text-center text-xs text-sky-700 dark:text-sky-300">En attente de votre confirmation…</p>
					{:else}
						<button type="button" disabled={actionEnCours} class="mt-3 rounded-lg bg-sky-700 px-3 py-2 text-xs font-medium text-white disabled:opacity-40" on:click={commencerJumelage}>
							{actionEnCours ? 'Préparation…' : 'Commencer le jumelage'}
						</button>
					{/if}
				</div>
			{/if}

			{#if selection.champs.length}
				<div class="mt-5 grid gap-3">
					{#each selection.champs as champ (champ.key)}
						<div>
							<label class="text-xs font-medium" for={`messagerie-${champ.key}`}>{champ.label}{champ.required ? ' *' : ''}</label>
							<input
								id={`messagerie-${champ.key}`}
								value={valeurs[champ.key] ?? ''}
								on:input={(event) => (valeurs = { ...valeurs, [champ.key]: event.currentTarget.value })}
								type={champ.secret ? 'password' : 'text'}
								autocomplete="off"
								placeholder={champ.isSet ? 'Déjà enregistré — laisser vide pour conserver' : ''}
								class="mt-1.5 w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900"
							/>
							{#if champ.description}<p class="mt-1 text-pretty text-[11px] text-gray-400">{champ.description}</p>{/if}
						</div>
					{/each}
				</div>
			{/if}

			{#if messageAction}
				<div class="mt-3 rounded-xl border px-3 py-2 text-xs {messageAction.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300'}">
					{messageAction.texte}
				</div>
			{/if}

			<div class="mt-5 flex items-center justify-between gap-2">
				<div>
					{#if selection.configuree || selection.connectee}
						<button type="button" class="rounded-lg px-3 py-2 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/20" on:click={() => (aDeconnecter = selection)}>Déconnecter</button>
					{/if}
				</div>
				<div class="flex gap-2">
					{#if selection.configuree}
						<button type="button" disabled={actionEnCours} class="rounded-lg bg-gray-100 px-3 py-2 text-xs disabled:opacity-40 dark:bg-gray-850" on:click={tester}>Tester</button>
					{/if}
					<button type="button" disabled={actionEnCours} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900" on:click={enregistrer}>
						{actionEnCours ? 'Enregistrement…' : 'Enregistrer et tester'}
					</button>
				</div>
			</div>
		</div>
	{/if}
</Modal>

<ConfirmDialog
	show={Boolean(aDeconnecter)}
	title="Déconnecter ce canal ?"
	message="Les identifiants enregistrés seront retirés de Hermes et ce canal cessera de recevoir les messages."
	confirmLabel="Déconnecter"
	onConfirm={deconnecter}
	on:cancel={() => (aDeconnecter = null)}
/>
