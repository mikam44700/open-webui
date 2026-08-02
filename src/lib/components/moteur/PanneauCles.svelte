<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CarteCapacite, { type Capacite } from './CarteCapacite.svelte';
	import {
		enregistrerCleFournisseur,
		getClesFournisseurs,
		retirerCleFournisseur,
		verifierCleFournisseur
	} from '$lib/apis/hermes';

	type Cle = {
		id: string;
		provider: string;
		titre: string;
		description: string;
		isSet: boolean;
		redacted?: string | null;
		password: boolean;
		advanced: boolean;
	};

	let chargement = true;
	let erreur = '';
	let cles: Cle[] = [];
	let selection: Cle | null = null;
	let showSelection = false;
	let valeur = '';
	let actionEnCours = false;
	let messageAction = '';
	let aSupprimer: Cle | null = null;

	const normaliser = (reponse: Record<string, any>): Cle[] =>
		Object.entries(reponse ?? {})
			.filter(([, info]) => !info?.channel_managed && (info?.category === 'provider' || info?.provider))
			.map(([id, info]) => ({
				id,
				provider: info.provider || id.split('_')[0].toLowerCase(),
				titre: info.provider_label || id.replaceAll('_', ' '),
				description: info.description || `Clé utilisée par ${info.provider_label || id}.`,
				isSet: Boolean(info.is_set),
				redacted: info.redacted_value,
				password: info.is_password !== false,
				advanced: Boolean(info.advanced)
			}))
			.sort((a, b) => Number(b.isSet) - Number(a.isSet) || a.titre.localeCompare(b.titre, 'fr'));

	const charger = async () => {
		chargement = true;
		erreur = '';
		try {
			cles = normaliser(await getClesFournisseurs(localStorage.token));
		} catch (err) {
			erreur = `${err}`;
		} finally {
			chargement = false;
		}
	};

	const ouvrir = (cle: Cle) => {
		selection = cle;
		showSelection = true;
		valeur = '';
		messageAction = '';
	};

	const fermer = () => {
		selection = null;
		showSelection = false;
		valeur = '';
		messageAction = '';
	};

	const enregistrer = async () => {
		if (!selection || !valeur.trim() || actionEnCours) return;
		actionEnCours = true;
		messageAction = '';
		try {
			const verification = await verifierCleFournisseur(
				localStorage.token,
				selection.id,
				valeur.trim()
			);
			if (verification?.reachable !== false && verification?.ok !== true) {
				messageAction = verification?.message || 'Cette clé a été refusée par le fournisseur.';
				return;
			}
			await enregistrerCleFournisseur(localStorage.token, selection.id, valeur.trim());
			toast.success(`${selection.titre} est connecté`);
			fermer();
			await charger();
		} catch (err) {
			messageAction = `${err}`;
		} finally {
			actionEnCours = false;
		}
	};

	const supprimer = async () => {
		if (!aSupprimer) return;
		actionEnCours = true;
		try {
			await retirerCleFournisseur(localStorage.token, aSupprimer.id);
			toast.success(`${aSupprimer.titre} est déconnecté`);
			aSupprimer = null;
			fermer();
			await charger();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			actionEnCours = false;
		}
	};

	const enCapacite = (cle: Cle): Capacite => ({
		id: cle.provider,
		titre: cle.titre,
		description: cle.description,
		detail: cle.isSet ? cle.redacted || 'Clé enregistrée' : cle.id,
		connecte: cle.isSet
	});

	$: connectees = cles.filter((cle) => cle.isSet);
	$: disponibles = cles.filter((cle) => !cle.isSet);

	onMount(charger);
</script>

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500">
		<Spinner className="size-4" /> Lecture des fournisseurs…
	</div>
{:else if erreur}
	<div class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">
		{erreur}
	</div>
{:else if cles.length === 0}
	<div class="rounded-2xl border border-dashed border-gray-300 px-5 py-14 text-center dark:border-gray-700">
		<p class="text-pretty text-sm text-gray-500">Hermes ne propose aucune clé fournisseur sur cette installation.</p>
		<button type="button" class="mt-3 rounded-lg bg-gray-100 px-3 py-1.5 text-xs dark:bg-gray-850" on:click={charger}>
			Relire le moteur
		</button>
	</div>
{:else}
	{#if connectees.length}
		<section class="mb-7">
			<h3 class="mb-3 text-sm font-medium">Connectés <span class="text-gray-400">({connectees.length})</span></h3>
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each connectees as cle (cle.id)}
					<CarteCapacite
						capacite={enCapacite(cle)}
						famille="modele"
						actionLabel="Gérer"
						on:action={() => ouvrir(cle)}
					/>
				{/each}
			</div>
		</section>
	{/if}

	<section>
		<h3 class="mb-3 text-sm font-medium">{connectees.length ? 'À découvrir' : 'Fournisseurs disponibles'}</h3>
		<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
			{#each disponibles as cle (cle.id)}
				<CarteCapacite
					capacite={enCapacite(cle)}
					famille="modele"
					actionLabel="Ajouter la clé"
					on:action={() => ouvrir(cle)}
				/>
			{/each}
		</div>
	</section>
{/if}

<Modal bind:show={showSelection} size="sm">
	{#if selection}
		<form class="p-5" on:submit|preventDefault={enregistrer}>
			<div class="flex items-start justify-between gap-4">
				<div>
					<h2 class="text-balance text-lg font-semibold">{selection.titre}</h2>
					<p class="mt-1 text-pretty text-xs text-gray-500">{selection.description}</p>
				</div>
				<button type="button" aria-label="Fermer" class="flex size-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850" on:click={fermer}>×</button>
			</div>

			<label class="mt-5 block text-xs font-medium" for="cle-fournisseur">Clé API</label>
			<input
				id="cle-fournisseur"
				bind:value={valeur}
				type={selection.password ? 'password' : 'text'}
				autocomplete="off"
				placeholder={selection.isSet ? 'Laisser vide pour conserver la clé actuelle' : 'Coller la clé ici'}
				class="mt-1.5 w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm outline-hidden focus:border-gray-400 dark:border-gray-800 dark:bg-gray-900"
			/>
			<p class="mt-2 text-pretty text-[11px] text-gray-400">
				La clé est vérifiée puis enregistrée dans Hermes. LunarIA ne la relit jamais en clair.
			</p>

			{#if messageAction}
				<div class="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">
					{messageAction}
				</div>
			{/if}

			<div class="mt-5 flex items-center justify-between gap-2">
				<div>
					{#if selection.isSet}
						<button type="button" class="rounded-lg px-3 py-2 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/20" on:click={() => (aSupprimer = selection)}>
							Retirer la clé
						</button>
					{/if}
				</div>
				<div class="flex gap-2">
					<button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs dark:bg-gray-850" on:click={fermer}>Annuler</button>
					<button type="submit" disabled={!valeur.trim() || actionEnCours} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900">
						{actionEnCours ? 'Vérification…' : selection.isSet ? 'Remplacer' : 'Vérifier et enregistrer'}
					</button>
				</div>
			</div>
		</form>
	{/if}
</Modal>

<ConfirmDialog
	show={Boolean(aSupprimer)}
	title="Retirer cette clé ?"
	message="Le fournisseur ne sera plus disponible pour les prochaines tâches utilisant cette clé."
	confirmLabel="Retirer"
	onConfirm={supprimer}
	on:cancel={() => (aSupprimer = null)}
/>
