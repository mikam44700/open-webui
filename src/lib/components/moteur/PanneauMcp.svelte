<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CarteCapacite, { type Capacite } from './CarteCapacite.svelte';
	import CatalogueCapacites from './CatalogueCapacites.svelte';
	import {
		ajouterServeurMcp,
		authentifierServeurMcp,
		basculerServeurMcp,
		getCatalogueMcp,
		getServeursMcp,
		installerMcp,
		retirerServeurMcp,
		suivreAuthentificationMcp,
		testerServeurMcp
	} from '$lib/apis/hermes';

	type Serveur = {
		id: string;
		titre: string;
		description: string;
		detail: string;
		actif: boolean;
		connecte: boolean;
		auth: string;
	};

	type Entree = {
		id: string;
		titre: string;
		description: string;
		categorie: string;
		installee: boolean;
		active: boolean;
		requiredEnv: { key: string; label: string; required: boolean }[];
	};

	const POPULAIRES = ['gmail', 'google-calendar', 'notion', 'slack', 'stripe', 'hubspot', 'data-gouv-fr'];

	let chargement = true;
	let erreur = '';
	let serveurs: Serveur[] = [];
	let catalogue: Entree[] = [];
	let showCatalogue = false;
	let selectionServeur: Serveur | null = null;
	let selectionEntree: Entree | null = null;
	let showServeur = false;
	let showEntree = false;
	let showPersonnalise = false;
	let aSupprimer: Serveur | null = null;
	let actionEnCours = new Set<string>();
	let messageAction: { ok: boolean; texte: string } | null = null;
	let env: Record<string, string> = {};
	let nom = '';
	let transport = 'http';
	let url = '';
	let commande = '';
	let argumentsTexte = '';
	let flowId = '';
	let minuterie: ReturnType<typeof setInterval> | null = null;

	const normaliserServeurs = (reponse: any): Serveur[] => {
		const source = reponse?.servers ?? reponse?.items ?? reponse ?? [];
		const entrees: Array<[string, any]> = Array.isArray(source)
			? source.map((item: any) => [`${item.name || item.id || ''}`, item])
			: Object.entries(source);
		return entrees
			.map(([id, valeur]: [string, any]) => ({
				id: `${id}`,
				titre: `${valeur.display_name ?? valeur.label ?? valeur.name ?? id}`,
				description: valeur.description || valeur.url || valeur.command || 'Serveur MCP personnalisé.',
				detail: `${valeur.transport ?? valeur.type ?? valeur.state ?? ''}`,
				actif: valeur.enabled !== false,
				connecte: ['connected', 'ready', 'ok'].includes(`${valeur.state ?? valeur.status ?? ''}`.toLowerCase()),
				auth: `${valeur.auth_type ?? valeur.auth ?? ''}`
			}))
			.filter((serveur: Serveur) => serveur.id);
	};

	const normaliserCatalogue = (reponse: any): Entree[] =>
		(reponse?.entries ?? reponse?.catalog ?? [])
			.map((entree: any) => ({
				id: `${entree.name ?? entree.id ?? ''}`,
				titre: `${entree.display_name ?? entree.label ?? entree.name ?? ''}`,
				description: entree.description || 'Connecteur spécialisé approuvé par Hermes.',
				categorie: entree.category || 'Autres',
				installee: Boolean(entree.installed),
				active: Boolean(entree.enabled),
				requiredEnv: (entree.required_env ?? []).map((champ: any) => ({
					key: `${champ.key ?? champ.name ?? champ}`,
					label: `${champ.label ?? champ.name ?? champ}`.replaceAll('_', ' '),
					required: champ.required !== false
				}))
			}))
			.filter((entree: Entree) => entree.id);

	const charger = async () => {
		chargement = true;
		erreur = '';
		try {
			const [liste, cat] = await Promise.all([
				getServeursMcp(localStorage.token),
				getCatalogueMcp(localStorage.token)
			]);
			serveurs = normaliserServeurs(liste);
			catalogue = normaliserCatalogue(cat);
		} catch (err) {
			erreur = `${err}`;
		} finally {
			chargement = false;
		}
	};

	const marquer = (id: string, actif: boolean) => {
		const suivant = new Set(actionEnCours);
		if (actif) suivant.add(id);
		else suivant.delete(id);
		actionEnCours = suivant;
	};

	const basculer = async (serveur: Serveur, actif: boolean) => {
		marquer(serveur.id, true);
		try {
			await basculerServeurMcp(localStorage.token, serveur.id, actif);
			serveurs = serveurs.map((item) => (item.id === serveur.id ? { ...item, actif } : item));
			toast.success(`${serveur.titre} est ${actif ? 'activé' : 'désactivé'}`);
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			marquer(serveur.id, false);
		}
	};

	const tester = async () => {
		if (!selectionServeur || actionEnCours.has(selectionServeur.id)) return;
		marquer(selectionServeur.id, true);
		messageAction = null;
		try {
			const resultat = await testerServeurMcp(localStorage.token, selectionServeur.id);
			const ok = Boolean(resultat?.ok ?? resultat?.connected ?? resultat?.success);
			messageAction = {
				ok,
				texte:
					resultat?.message ||
					(ok
						? `${resultat?.tools?.length ?? resultat?.tool_count ?? 0} outil(s) détecté(s).`
						: 'Le serveur ne répond pas.')
			};
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			marquer(selectionServeur.id, false);
		}
	};

	const ouvrirEntree = (capacite: Capacite) => {
		const entree = catalogue.find((item) => item.id === capacite.id);
		if (!entree) return;
		selectionEntree = entree;
		showEntree = true;
		env = {};
		messageAction = null;
		showCatalogue = false;
	};

	const installer = async () => {
		if (!selectionEntree || actionEnCours.has(selectionEntree.id)) return;
		const entree = selectionEntree;
		marquer(entree.id, true);
		messageAction = null;
		try {
			await installerMcp(
				localStorage.token,
				entree.id,
				Object.fromEntries(Object.entries(env).filter(([, valeur]) => valeur.trim())),
				true
			);
			toast.success(`${entree.titre} est installé`);
			selectionEntree = null;
			showEntree = false;
			await charger();
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			marquer(entree.id, false);
		}
	};

	const ajouterPersonnalise = async () => {
		if (!nom.trim() || actionEnCours.has('custom')) return;
		marquer('custom', true);
		messageAction = null;
		try {
			const corps =
				transport === 'http'
					? { name: nom.trim(), url: url.trim(), transport: 'http' }
					: {
							name: nom.trim(),
							command: commande.trim(),
							args: argumentsTexte.split(/\s+/).filter(Boolean),
							transport: 'stdio'
						};
			await ajouterServeurMcp(localStorage.token, corps);
			toast.success(`${nom.trim()} est ajouté`);
			showPersonnalise = false;
			await charger();
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			marquer('custom', false);
		}
	};

	const supprimer = async () => {
		if (!aSupprimer) return;
		marquer(aSupprimer.id, true);
		try {
			await retirerServeurMcp(localStorage.token, aSupprimer.id);
			toast.success(`${aSupprimer.titre} a été retiré`);
			aSupprimer = null;
			selectionServeur = null;
			showServeur = false;
			await charger();
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			if (aSupprimer) marquer(aSupprimer.id, false);
		}
	};

	const authentifier = async () => {
		if (!selectionServeur) return;
		marquer(selectionServeur.id, true);
		messageAction = null;
		try {
			const resultat = await authentifierServeurMcp(localStorage.token, selectionServeur.id);
			const urlAuth = resultat?.authorization_url || resultat?.auth_url || resultat?.url;
			flowId = `${resultat?.flow_id ?? resultat?.id ?? ''}`;
			if (urlAuth) window.open(urlAuth, '_blank', 'noopener,noreferrer');
			if (flowId) {
				if (minuterie) clearInterval(minuterie);
				minuterie = setInterval(suivreAuth, 2000);
			}
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			marquer(selectionServeur.id, false);
		}
	};

	async function suivreAuth() {
		if (!flowId) return;
		try {
			const resultat = await suivreAuthentificationMcp(localStorage.token, flowId);
			const statut = `${resultat?.status ?? resultat?.state ?? ''}`.toLowerCase();
			if (['connected', 'complete', 'completed', 'success'].includes(statut)) {
				if (minuterie) clearInterval(minuterie);
				minuterie = null;
				flowId = '';
				toast.success('Authentification MCP terminée');
				await charger();
			} else if (['error', 'denied', 'expired'].includes(statut)) {
				if (minuterie) clearInterval(minuterie);
				minuterie = null;
				messageAction = { ok: false, texte: resultat?.error || `Authentification ${statut}.` };
			}
		} catch (err) {
			if (minuterie) clearInterval(minuterie);
			minuterie = null;
			messageAction = { ok: false, texte: `${err}` };
		}
	}

	const serveurCapacite = (serveur: Serveur): Capacite => ({
		id: serveur.id,
		titre: serveur.titre,
		description: serveur.description,
		detail: serveur.detail,
		actif: serveur.actif,
		connecte: serveur.connecte
	});

	const entreeCapacite = (entree: Entree): Capacite => ({
		id: entree.id,
		titre: entree.titre,
		description: entree.description,
		categorie: entree.categorie,
		actif: entree.active,
		connecte: entree.installee
	});

	$: idsInstalles = new Set(serveurs.map((serveur) => serveur.id));
	$: aDecouvrir = catalogue.filter((entree) => !entree.installee && !idsInstalles.has(entree.id));
	$: vedettes = POPULAIRES.map((id) => aDecouvrir.find((entree) => entree.id === id))
		.filter(Boolean)
		.concat(aDecouvrir.filter((entree) => !POPULAIRES.includes(entree.id)))
		.slice(0, 6) as Entree[];

	onMount(charger);
	onDestroy(() => {
		if (minuterie) clearInterval(minuterie);
	});
</script>

<div class="mb-5 flex justify-end">
	<button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs text-gray-700 hover:bg-gray-200 dark:bg-gray-850 dark:text-gray-200 dark:hover:bg-gray-800" on:click={() => {
		nom = '';
		transport = 'http';
		url = '';
		commande = '';
		argumentsTexte = '';
		messageAction = null;
		showPersonnalise = true;
	}}>Ajouter un connecteur personnalisé</button>
</div>

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500"><Spinner className="size-4" /> Lecture des connecteurs…</div>
{:else if erreur}
	<div class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">{erreur}</div>
{:else}
	{#if serveurs.length}
		<section class="mb-8">
			<h3 class="mb-3 text-sm font-medium">Connecteurs installés <span class="text-gray-400">({serveurs.length})</span></h3>
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each serveurs as serveur (serveur.id)}
					<CarteCapacite
						capacite={serveurCapacite(serveur)}
						famille="mcp"
						basculable
						actionLabel="Gérer"
						enCours={actionEnCours.has(serveur.id)}
						on:toggle={(event) => basculer(serveur, event.detail.actif)}
						on:action={() => {
							selectionServeur = serveur;
							showServeur = true;
							messageAction = null;
						}}
					/>
				{/each}
			</div>
		</section>
	{/if}

	<section>
		<div class="mb-3 flex items-center justify-between gap-3">
			<h3 class="text-sm font-medium">{serveurs.length ? 'À découvrir' : 'Les plus populaires'}</h3>
			<button type="button" class="rounded-lg px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-850" on:click={() => (showCatalogue = true)}>Tout parcourir</button>
		</div>
		{#if vedettes.length}
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each vedettes as entree (entree.id)}
					<CarteCapacite capacite={entreeCapacite(entree)} famille="mcp" actionLabel="Installer" on:action={() => ouvrirEntree(entreeCapacite(entree))} />
				{/each}
			</div>
		{:else}
			<div class="rounded-2xl border border-dashed border-gray-300 px-5 py-12 text-center dark:border-gray-700">
				<p class="text-sm text-gray-500">Tous les connecteurs proposés sont déjà installés.</p>
				<button type="button" class="mt-3 rounded-lg bg-gray-100 px-3 py-1.5 text-xs dark:bg-gray-850" on:click={() => (showCatalogue = true)}>Voir le catalogue</button>
			</div>
		{/if}
	</section>
{/if}

<CatalogueCapacites
	bind:show={showCatalogue}
	titre="Catalogue des connecteurs MCP"
	elements={aDecouvrir.map(entreeCapacite)}
	famille="mcp"
	actionLabel="Installer"
	onAction={ouvrirEntree}
/>

<Modal bind:show={showEntree} size="sm">
	{#if selectionEntree}
		<form class="p-5" on:submit|preventDefault={installer}>
			<div class="flex items-start justify-between gap-4">
				<div>
					<h2 class="text-balance text-lg font-semibold">{selectionEntree.titre}</h2>
					<p class="mt-1 text-pretty text-xs text-gray-500">{selectionEntree.description}</p>
				</div>
				<button type="button" aria-label="Fermer" class="flex size-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (showEntree = false)}>×</button>
			</div>
			{#if selectionEntree.requiredEnv.length}
				<div class="mt-5 grid gap-3">
					{#each selectionEntree.requiredEnv as champ (champ.key)}
						<div>
							<label class="text-xs font-medium" for={`mcp-${champ.key}`}>{champ.label}{champ.required ? ' *' : ''}</label>
							<input id={`mcp-${champ.key}`} value={env[champ.key] ?? ''} on:input={(event) => (env = { ...env, [champ.key]: event.currentTarget.value })} type="password" autocomplete="off" class="mt-1.5 w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" />
						</div>
					{/each}
				</div>
			{:else}
				<div class="mt-5 rounded-xl bg-gray-50 px-3.5 py-3 text-xs text-gray-600 dark:bg-gray-850 dark:text-gray-300">Ce connecteur ne demande aucune clé avant installation.</div>
			{/if}
			{#if messageAction}<div class="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">{messageAction.texte}</div>{/if}
			<div class="mt-5 flex justify-end gap-2">
				<button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs dark:bg-gray-850" on:click={() => (showEntree = false)}>Annuler</button>
				<button type="submit" disabled={actionEnCours.has(selectionEntree.id)} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900">{actionEnCours.has(selectionEntree.id) ? 'Installation…' : 'Installer'}</button>
			</div>
		</form>
	{/if}
</Modal>

<Modal bind:show={showPersonnalise} size="sm">
	<form class="p-5" on:submit|preventDefault={ajouterPersonnalise}>
		<div class="flex items-start justify-between gap-4">
			<div>
				<h2 class="text-balance text-lg font-semibold">Connecteur MCP personnalisé</h2>
				<p class="mt-1 text-pretty text-xs text-gray-500">Branchez une adresse HTTP ou une commande locale connue.</p>
			</div>
			<button type="button" aria-label="Fermer" class="flex size-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (showPersonnalise = false)}>×</button>
		</div>
		<div class="mt-5 grid gap-3">
			<label class="text-xs font-medium" for="mcp-nom">Nom</label>
			<input id="mcp-nom" bind:value={nom} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" />
			<label class="text-xs font-medium" for="mcp-transport">Type de connexion</label>
			<select id="mcp-transport" bind:value={transport} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900">
				<option value="http">Adresse HTTP</option>
				<option value="stdio">Commande locale (avancé)</option>
			</select>
			{#if transport === 'http'}
				<label class="text-xs font-medium" for="mcp-url">Adresse</label>
				<input id="mcp-url" bind:value={url} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="https://exemple.com/mcp" />
			{:else}
				<label class="text-xs font-medium" for="mcp-commande">Commande</label>
				<input id="mcp-commande" bind:value={commande} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="npx" />
				<label class="text-xs font-medium" for="mcp-arguments">Arguments</label>
				<input id="mcp-arguments" bind:value={argumentsTexte} class="-mt-1.5 rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="-y @serveur/mcp" />
			{/if}
		</div>
		{#if messageAction}<div class="mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">{messageAction.texte}</div>{/if}
		<div class="mt-5 flex justify-end gap-2">
			<button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs dark:bg-gray-850" on:click={() => (showPersonnalise = false)}>Annuler</button>
			<button type="submit" disabled={!nom.trim() || (transport === 'http' ? !url.trim() : !commande.trim()) || actionEnCours.has('custom')} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900">Ajouter</button>
		</div>
	</form>
</Modal>

<Modal bind:show={showServeur} size="sm">
	{#if selectionServeur}
		<div class="p-5">
			<div class="flex items-start justify-between gap-4">
				<div>
					<h2 class="text-balance text-lg font-semibold">{selectionServeur.titre}</h2>
					<p class="mt-1 text-pretty text-xs text-gray-500">{selectionServeur.description}</p>
				</div>
				<button type="button" aria-label="Fermer" class="flex size-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (showServeur = false)}>×</button>
			</div>
			{#if messageAction}<div class="mt-4 rounded-xl border px-3 py-2 text-xs {messageAction.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300'}">{messageAction.texte}</div>{/if}
			<div class="mt-5 flex flex-wrap items-center justify-between gap-2">
				<button type="button" class="rounded-lg px-3 py-2 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/20" on:click={() => (aSupprimer = selectionServeur)}>Retirer</button>
				<div class="flex gap-2">
					{#if selectionServeur.auth === 'oauth'}<button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs dark:bg-gray-850" on:click={authentifier}>S’authentifier</button>{/if}
					<button type="button" disabled={actionEnCours.has(selectionServeur.id)} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900" on:click={tester}>{actionEnCours.has(selectionServeur.id) ? 'Test…' : 'Tester la connexion'}</button>
				</div>
			</div>
		</div>
	{/if}
</Modal>

<ConfirmDialog
	show={Boolean(aSupprimer)}
	title="Retirer ce connecteur MCP ?"
	message="Hermes perdra immédiatement les outils fournis par ce serveur."
	confirmLabel="Retirer"
	onConfirm={supprimer}
	on:cancel={() => (aSupprimer = null)}
/>
