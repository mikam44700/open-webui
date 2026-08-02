<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CarteCapacite, { type Capacite } from './CarteCapacite.svelte';
	import {
		activerServeurPersonnalise,
		enregistrerServeurPersonnalise,
		getServeursPersonnalises,
		retirerServeurPersonnalise,
		verifierServeurPersonnalise
	} from '$lib/apis/hermes';

	type Serveur = {
		id: string;
		titre: string;
		baseUrl: string;
		model: string;
		actif: boolean;
	};

	let chargement = true;
	let erreur = '';
	let serveurs: Serveur[] = [];
	let show = false;
	let edition: Serveur | null = null;
	let aSupprimer: Serveur | null = null;
	let nom = '';
	let baseUrl = 'http://host.docker.internal:11434/v1';
	let modele = '';
	let cle = '';
	let modelesTrouves: string[] = [];
	let actionEnCours = false;
	let messageAction = '';

	const normaliser = (reponse: any): Serveur[] => {
		const source = reponse?.endpoints ?? reponse?.providers ?? reponse?.items ?? reponse ?? [];
		const entrees: Array<[string, any]> = Array.isArray(source)
			? source.map((item: any) => [`${item.id || item.name || ''}`, item])
			: Object.entries(source);
		return entrees
			.map(([id, valeur]: [string, any]) => ({
				id: `${id}`,
				titre: `${valeur.name ?? valeur.label ?? id}`,
				baseUrl: `${valeur.base_url ?? valeur.url ?? ''}`,
				model: `${valeur.model ?? valeur.default_model ?? ''}`,
				actif: Boolean(valeur.active ?? valeur.is_active ?? valeur.default)
			}))
			.filter((serveur: Serveur) => serveur.id);
	};

	const charger = async () => {
		chargement = true;
		erreur = '';
		try {
			serveurs = normaliser(await getServeursPersonnalises(localStorage.token));
		} catch (err) {
			erreur = `${err}`;
		} finally {
			chargement = false;
		}
	};

	const ouvrir = (serveur: Serveur | null = null) => {
		edition = serveur;
		nom = serveur?.titre ?? '';
		baseUrl = serveur?.baseUrl ?? 'http://host.docker.internal:11434/v1';
		modele = serveur?.model ?? '';
		cle = '';
		modelesTrouves = [];
		messageAction = '';
		show = true;
	};

	const corps = () => ({
		id: edition?.id ?? '',
		name: nom.trim(),
		base_url: baseUrl.trim().replace(/\/$/, ''),
		model: modele.trim(),
		api_key: cle || undefined,
		discover_models: true,
		make_default: edition?.actif ?? false
	});

	const tester = async () => {
		if (!nom.trim() || !baseUrl.trim() || actionEnCours) return;
		actionEnCours = true;
		messageAction = '';
		try {
			const resultat = await verifierServeurPersonnalise(localStorage.token, corps());
			modelesTrouves = resultat?.models ?? [];
			if (!resultat?.ok) {
				messageAction = resultat?.message || 'Ce serveur n’a pas répondu correctement.';
				return;
			}
			if (!modele && modelesTrouves.length) modele = modelesTrouves[0];
			messageAction = `${modelesTrouves.length || 1} modèle${modelesTrouves.length > 1 ? 's' : ''} détecté${modelesTrouves.length > 1 ? 's' : ''}.`;
		} catch (err) {
			messageAction = `${err}`;
		} finally {
			actionEnCours = false;
		}
	};

	const enregistrer = async () => {
		if (!nom.trim() || !baseUrl.trim() || !modele.trim() || actionEnCours) return;
		actionEnCours = true;
		messageAction = '';
		try {
			await enregistrerServeurPersonnalise(localStorage.token, corps());
			toast.success(`${nom.trim()} est enregistré`);
			show = false;
			await charger();
		} catch (err) {
			messageAction = `${err}`;
		} finally {
			actionEnCours = false;
		}
	};

	const activer = async (serveur: Serveur) => {
		actionEnCours = true;
		try {
			await activerServeurPersonnalise(localStorage.token, serveur.id);
			toast.success(`${serveur.titre} devient le serveur actif`);
			await charger();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			actionEnCours = false;
		}
	};

	const supprimer = async () => {
		if (!aSupprimer) return;
		actionEnCours = true;
		try {
			await retirerServeurPersonnalise(localStorage.token, aSupprimer.id);
			toast.success(`${aSupprimer.titre} a été retiré`);
			aSupprimer = null;
			show = false;
			await charger();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			actionEnCours = false;
		}
	};

	const enCapacite = (serveur: Serveur): Capacite => ({
		id: serveur.id,
		titre: serveur.titre,
		description: serveur.baseUrl,
		detail: serveur.model,
		connecte: serveur.actif
	});

	onMount(charger);
</script>

<div class="mb-4 flex justify-end">
	<button type="button" class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white dark:bg-white dark:text-gray-900" on:click={() => ouvrir()}>
		Ajouter un serveur local
	</button>
</div>

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500"><Spinner className="size-4" /> Lecture des serveurs…</div>
{:else if erreur}
	<div class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">{erreur}</div>
{:else if serveurs.length === 0}
	<div class="rounded-2xl border border-dashed border-gray-300 px-5 py-14 text-center dark:border-gray-700">
		<p class="text-pretty text-sm text-gray-500">Aucun serveur local ou OpenAI-compatible n’est encore déclaré.</p>
		<button type="button" class="mt-3 rounded-lg bg-gray-100 px-3 py-1.5 text-xs dark:bg-gray-850" on:click={() => ouvrir()}>Ajouter le premier</button>
	</div>
{:else}
	<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
		{#each serveurs as serveur (serveur.id)}
			<CarteCapacite
				capacite={enCapacite(serveur)}
				famille="modele"
				actionLabel={serveur.actif ? 'Gérer' : 'Utiliser'}
				secondaire="Modifier"
				enCours={actionEnCours}
				on:action={() => (serveur.actif ? ouvrir(serveur) : activer(serveur))}
				on:secondary={() => ouvrir(serveur)}
			/>
		{/each}
	</div>
{/if}

<Modal bind:show size="sm">
	<form class="p-5" on:submit|preventDefault={enregistrer}>
		<div class="flex items-start justify-between gap-4">
			<div>
				<h2 class="text-balance text-lg font-semibold">{edition ? 'Modifier le serveur' : 'Ajouter un serveur local'}</h2>
				<p class="mt-1 text-pretty text-xs text-gray-500">Compatible avec Ollama, LM Studio, vLLM et toute API au format OpenAI.</p>
			</div>
			<button type="button" aria-label="Fermer" class="flex size-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (show = false)}>×</button>
		</div>

		<div class="mt-5 grid gap-3">
			<label class="text-xs font-medium" for="serveur-nom">Nom</label>
			<input id="serveur-nom" bind:value={nom} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Ollama sur mon Mac" />
			<label class="text-xs font-medium" for="serveur-url">Adresse de l’API</label>
			<input id="serveur-url" bind:value={baseUrl} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="http://host.docker.internal:11434/v1" />
			<label class="text-xs font-medium" for="serveur-cle">Clé API <span class="font-normal text-gray-400">(si nécessaire)</span></label>
			<input id="serveur-cle" bind:value={cle} type="password" autocomplete="off" class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder={edition ? 'Laisser vide pour conserver' : 'Facultatif'} />
			<label class="text-xs font-medium" for="serveur-modele">Modèle</label>
			{#if modelesTrouves.length}
				<select id="serveur-modele" bind:value={modele} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900">
					{#each modelesTrouves as item}<option value={item}>{item}</option>{/each}
				</select>
			{:else}
				<input id="serveur-modele" bind:value={modele} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Testez l’adresse pour détecter les modèles" />
			{/if}
		</div>

		{#if messageAction}
			<div class="mt-3 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700 dark:border-gray-800 dark:bg-gray-850 dark:text-gray-300">{messageAction}</div>
		{/if}

		<div class="mt-5 flex items-center justify-between gap-2">
			<div>
				{#if edition}
					<button type="button" class="rounded-lg px-3 py-2 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/20" on:click={() => (aSupprimer = edition)}>Retirer</button>
				{/if}
			</div>
			<div class="flex gap-2">
				<button type="button" disabled={!nom.trim() || !baseUrl.trim() || actionEnCours} class="rounded-lg bg-gray-100 px-3 py-2 text-xs disabled:opacity-40 dark:bg-gray-850" on:click={tester}>{actionEnCours ? 'Test…' : 'Tester'}</button>
				<button type="submit" disabled={!nom.trim() || !baseUrl.trim() || !modele.trim() || actionEnCours} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900">Enregistrer</button>
			</div>
		</div>
	</form>
</Modal>

<ConfirmDialog
	show={Boolean(aSupprimer)}
	title="Retirer ce serveur ?"
	message="Cette adresse et sa clé seront supprimées de Hermes."
	confirmLabel="Retirer"
	onConfirm={supprimer}
	on:cancel={() => (aSupprimer = null)}
/>
