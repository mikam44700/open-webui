<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CarteCapacite, { type Capacite } from './CarteCapacite.svelte';
	import CatalogueCapacites from './CatalogueCapacites.svelte';
	import type { FamilleLogo } from './logos';
	import {
		basculerOutil,
		choisirFournisseurOutil,
		choisirModeleOutil,
		enregistrerClesOutil,
		finaliserConfigurationOutil,
		getConfigurationOutil,
		getInventaireOutils,
		getModelesOutil
	} from '$lib/apis/hermes';

	export let mode: 'integrations' | 'recherche' | 'outils' = 'outils';

	type Outil = {
		id: string;
		titre: string;
		description: string;
		actif: boolean;
		configure: boolean;
		categorie: string;
	};

	type Champ = {
		key: string;
		label: string;
		required: boolean;
		isSet: boolean;
		secret: boolean;
	};

	type Fournisseur = {
		id: string;
		titre: string;
		description: string;
		actif: boolean;
		pret: boolean;
		advanced: boolean;
		capabilities: string[];
		champs: Champ[];
		postSetup?: string;
	};

	const MOTS_RECHERCHE = ['search', 'web', 'browser', 'crawl', 'fetch', 'scrape', 'http', 'x_search'];
	const MOTS_INTEGRATION = [
		'google',
		'gmail',
		'calendar',
		'drive',
		'notion',
		'github',
		'slack',
		'linear',
		'jira',
		'discord',
		'telegram',
		'whatsapp',
		'email',
		'smtp',
		'integration',
		'automation',
		'homeassistant'
	];

	const CATEGORIES: Record<string, string[]> = {
		'Recherche & Web': MOTS_RECHERCHE,
		'Communication & Applications': MOTS_INTEGRATION,
		'Création de contenu': ['image', 'video', 'audio', 'tts', 'stt', 'vision'],
		'Mémoire & Contexte': ['memory', 'context', 'session', 'todo'],
		'Fichiers & Données': ['file', 'document', 'pdf', 'spreadsheet', 'database', 'sql'],
		'Système & Code': ['terminal', 'code', 'computer', 'shell', 'git', 'python']
	};

	let chargement = true;
	let erreur = '';
	let tous: Outil[] = [];
	let showCatalogue = false;
	let selection: Outil | null = null;
	let showSelection = false;
	let configurationChargee = false;
	let fournisseurs: Fournisseur[] = [];
	let fournisseurActif = '';
	let fournisseurSelectionne = '';
	let valeurs: Record<string, string> = {};
	let modeles: string[] = [];
	let modele = '';
	let actionEnCours = new Set<string>();
	let messageAction: { ok: boolean; texte: string } | null = null;
	let famille: FamilleLogo = 'outil';

	const appartient = (outil: Outil, mots: string[]) => {
		const texte = `${outil.id} ${outil.titre}`.toLowerCase();
		return mots.some((mot) => texte.includes(mot));
	};

	const categoriePour = (id: string, titre: string) => {
		const texte = `${id} ${titre}`.toLowerCase();
		return (
			Object.entries(CATEGORIES).find(([, mots]) => mots.some((mot) => texte.includes(mot)))?.[0] ??
			'Autres'
		);
	};

	const normaliserInventaire = (reponse: any): Outil[] => {
		const source = reponse?.toolsets ?? reponse?.items ?? reponse ?? [];
		const entrees: Array<[string, any]> = Array.isArray(source)
			? source.map((item: any) => [`${item.name || item.id || ''}`, item])
			: Object.entries(source);
		return entrees
			.map(([id, valeur]: [string, any]) => {
				const titre = `${valeur.label ?? valeur.display_name ?? valeur.name ?? id}`;
				return {
					id: `${id}`,
					titre,
					description: valeur.description || valeur.summary || 'Capacité native du moteur Hermes.',
					actif: Boolean(valeur.enabled ?? valeur.active),
					configure: Boolean(valeur.configured ?? valeur.ready),
					categorie: categoriePour(`${id}`, titre)
				};
			})
			.filter((outil: Outil) => outil.id);
	};

	const normaliserConfiguration = (reponse: any): Fournisseur[] =>
		(reponse?.providers ?? [])
			.map((provider: any) => ({
				id: `${provider.name ?? provider.id ?? ''}`,
				titre: `${provider.label ?? provider.display_name ?? provider.name ?? ''}`,
				description: provider.description || 'Fournisseur proposé par Hermes.',
				actif: Boolean(provider.is_active ?? provider.active),
				pret:
					['ready', 'connected', 'configured'].includes(`${provider.status ?? ''}`.toLowerCase()) ||
					Boolean(provider.configured),
				advanced: Boolean(provider.advanced),
				capabilities: provider.capabilities ?? [],
				champs: (provider.env_vars ?? []).map((champ: any) => ({
					key: `${champ.key ?? champ.name ?? ''}`,
					label: `${champ.label ?? champ.name ?? champ.key ?? ''}`.replaceAll('_', ' '),
					required: champ.required !== false,
					isSet: Boolean(champ.is_set),
					secret: /(TOKEN|SECRET|PASSWORD|KEY)/.test(`${champ.key ?? champ.name ?? ''}`)
				})),
				postSetup: provider.post_setup_key || provider.post_setup || undefined
			}))
			.filter((provider: Fournisseur) => provider.id);

	const charger = async () => {
		chargement = true;
		erreur = '';
		try {
			tous = normaliserInventaire(await getInventaireOutils(localStorage.token));
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

	const basculer = async (outil: Outil, actif: boolean) => {
		marquer(outil.id, true);
		try {
			await basculerOutil(localStorage.token, outil.id, actif);
			tous = tous.map((item) => (item.id === outil.id ? { ...item, actif } : item));
			toast.success(`${outil.titre} est ${actif ? 'activé' : 'désactivé'}`);
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			marquer(outil.id, false);
		}
	};

	const ouvrir = async (outil: Outil) => {
		selection = outil;
		showSelection = true;
		configurationChargee = false;
		fournisseurs = [];
		fournisseurActif = '';
		fournisseurSelectionne = '';
		valeurs = {};
		modeles = [];
		modele = '';
		messageAction = null;
		try {
			const reponse = await getConfigurationOutil(localStorage.token, outil.id);
			fournisseurs = normaliserConfiguration(reponse);
			fournisseurActif = `${reponse?.active_provider ?? ''}`;
			fournisseurSelectionne =
				fournisseurActif || fournisseurs.find((provider) => provider.pret)?.id || fournisseurs[0]?.id || '';
			if (fournisseurSelectionne) await chargerModeles(outil.id);
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			configurationChargee = true;
		}
	};

	const chargerModeles = async (outilId: string) => {
		try {
			const reponse = await getModelesOutil(localStorage.token, outilId);
			modeles = (reponse?.models ?? []).map((item: any) =>
				typeof item === 'string' ? item : `${item.id ?? item.name ?? ''}`
			).filter(Boolean);
			modele = `${reponse?.current ?? reponse?.default ?? modeles[0] ?? ''}`;
		} catch {
			modeles = [];
			modele = '';
		}
	};

	const enregistrer = async () => {
		if (!selection || actionEnCours.has(selection.id)) return;
		const outil = selection;
		marquer(selection.id, true);
		messageAction = null;
		try {
			const provider = fournisseurs.find((item) => item.id === fournisseurSelectionne);
			const env = Object.fromEntries(
				Object.entries(valeurs).filter(([, valeur]) => valeur.trim()).map(([key, valeur]) => [key, valeur.trim()])
			);
			if (Object.keys(env).length) {
				await enregistrerClesOutil(localStorage.token, selection.id, env);
			}
			if (fournisseurSelectionne) {
				await choisirFournisseurOutil(localStorage.token, outil.id, fournisseurSelectionne);
			}
			if (modele && fournisseurSelectionne) {
				await choisirModeleOutil(localStorage.token, outil.id, modele, fournisseurSelectionne);
			}
			if (provider?.postSetup) {
				await finaliserConfigurationOutil(localStorage.token, outil.id, provider.postSetup);
			}
			if (!outil.actif) await basculerOutil(localStorage.token, outil.id, true);
			messageAction = { ok: true, texte: 'Configuration enregistrée dans Hermes.' };
			toast.success(`${outil.titre} est prêt`);
			await charger();
		} catch (err) {
			messageAction = { ok: false, texte: `${err}` };
		} finally {
			marquer(outil.id, false);
		}
	};

	const enCapacite = (outil: Outil): Capacite => ({
		id: outil.id,
		titre: outil.titre,
		description: outil.description,
		detail: outil.configure ? 'Fournisseur configuré' : undefined,
		actif: outil.actif,
		connecte: outil.configure,
		categorie: outil.categorie
	});

	const depuisCapacite = (capacite: Capacite) => {
		const outil = visibles.find((item) => item.id === capacite.id);
		if (outil) ouvrir(outil);
	};

	$: visibles =
		mode === 'recherche'
			? tous.filter((outil) => appartient(outil, MOTS_RECHERCHE))
			: mode === 'integrations'
				? tous.filter((outil) => appartient(outil, MOTS_INTEGRATION))
				: tous.filter(
						(outil) =>
							!appartient(outil, MOTS_RECHERCHE) && !appartient(outil, MOTS_INTEGRATION)
					);
	$: actifs = visibles.filter((outil) => outil.actif || outil.configure);
	$: aDecouvrir = visibles.filter((outil) => !outil.actif && !outil.configure);
	$: vedettes = aDecouvrir.slice(0, 6);
	$: famille = mode === 'recherche' ? 'web' : mode === 'integrations' ? 'integration' : 'outil';
	$: fournisseurCourant = fournisseurs.find((provider) => provider.id === fournisseurSelectionne);

	onMount(charger);
</script>

{#if chargement}
	<div class="flex items-center justify-center gap-2 py-16 text-sm text-gray-500"><Spinner className="size-4" /> Lecture des capacités…</div>
{:else if erreur}
	<div class="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">{erreur}</div>
{:else if visibles.length === 0}
	<div class="rounded-2xl border border-dashed border-gray-300 px-5 py-14 text-center dark:border-gray-700">
		<p class="text-pretty text-sm text-gray-500">Hermes ne propose encore aucun élément dans cette famille.</p>
		<button type="button" class="mt-3 rounded-lg bg-gray-100 px-3 py-1.5 text-xs dark:bg-gray-850" on:click={charger}>Relire le moteur</button>
	</div>
{:else}
	{#if actifs.length}
		<section class="mb-8">
			<h3 class="mb-3 text-sm font-medium">{mode === 'integrations' ? 'Applications connectées' : 'Activés'} <span class="text-gray-400">({actifs.length})</span></h3>
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each actifs as outil (outil.id)}
					<CarteCapacite
						capacite={enCapacite(outil)}
						{famille}
						basculable
						actionLabel="Configurer"
						enCours={actionEnCours.has(outil.id)}
						on:toggle={(event) => basculer(outil, event.detail.actif)}
						on:action={() => ouvrir(outil)}
					/>
				{/each}
			</div>
		</section>
	{/if}

	<section>
		<div class="mb-3 flex items-center justify-between gap-3">
			<h3 class="text-sm font-medium">{actifs.length ? 'À découvrir' : 'Les plus populaires'}</h3>
			<button type="button" class="rounded-lg px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-850" on:click={() => (showCatalogue = true)}>Tout parcourir</button>
		</div>
		{#if vedettes.length}
			<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
				{#each vedettes as outil (outil.id)}
					<CarteCapacite capacite={enCapacite(outil)} {famille} actionLabel="Configurer" on:action={() => ouvrir(outil)} />
				{/each}
			</div>
		{:else}
			<div class="rounded-2xl border border-dashed border-gray-300 px-5 py-12 text-center dark:border-gray-700">
				<p class="text-sm text-gray-500">Tout ce que propose Hermes dans cette famille est déjà activé.</p>
				<button type="button" class="mt-3 rounded-lg bg-gray-100 px-3 py-1.5 text-xs dark:bg-gray-850" on:click={() => (showCatalogue = true)}>Voir la liste complète</button>
			</div>
		{/if}
	</section>
{/if}

<CatalogueCapacites
	bind:show={showCatalogue}
	titre={mode === 'integrations' ? 'Toutes les intégrations' : mode === 'recherche' ? 'Tous les services web' : 'Tous les outils'}
	elements={visibles.map(enCapacite)}
	{famille}
	actionLabel="Configurer"
	onAction={depuisCapacite}
/>

<Modal bind:show={showSelection} size="md">
	{#if selection}
		<div class="p-5">
			<div class="flex items-start justify-between gap-4">
				<div>
					<h2 class="text-balance text-lg font-semibold">{selection.titre}</h2>
					<p class="mt-1 text-pretty text-xs text-gray-500">{selection.description}</p>
				</div>
				<button type="button" aria-label="Fermer" class="flex size-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (showSelection = false)}>×</button>
			</div>

			{#if !configurationChargee}
				<div class="flex items-center justify-center gap-2 py-12 text-sm text-gray-500"><Spinner className="size-4" /> Lecture des fournisseurs…</div>
			{:else if fournisseurs.length === 0}
				<div class="mt-5 rounded-xl bg-gray-50 px-3.5 py-3 text-xs text-gray-600 dark:bg-gray-850 dark:text-gray-300">
					Aucune connexion supplémentaire n’est requise. Vous pouvez simplement activer cet outil.
				</div>
			{:else}
				<div class="mt-5">
					<label class="text-xs font-medium" for="outil-fournisseur">Fournisseur</label>
					<select
						id="outil-fournisseur"
						bind:value={fournisseurSelectionne}
						on:change={() => chargerModeles(selection?.id ?? '')}
						class="mt-1.5 w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900"
					>
						{#each fournisseurs.filter((provider) => !provider.advanced) as provider (provider.id)}
							<option value={provider.id}>{provider.titre}{provider.pret ? ' — prêt' : ''}</option>
						{/each}
						{#if fournisseurs.some((provider) => provider.advanced)}
							<optgroup label="Options avancées">
								{#each fournisseurs.filter((provider) => provider.advanced) as provider (provider.id)}
									<option value={provider.id}>{provider.titre}{provider.pret ? ' — prêt' : ''}</option>
								{/each}
							</optgroup>
						{/if}
					</select>
					{#if fournisseurCourant?.description}<p class="mt-1.5 text-pretty text-xs text-gray-500">{fournisseurCourant.description}</p>{/if}
				</div>

				{#if fournisseurCourant?.champs.length}
					<div class="mt-4 grid gap-3">
						{#each fournisseurCourant.champs as champ (champ.key)}
							<div>
								<label class="text-xs font-medium" for={`outil-${champ.key}`}>{champ.label}{champ.required ? ' *' : ''}</label>
								<input
									id={`outil-${champ.key}`}
									value={valeurs[champ.key] ?? ''}
									on:input={(event) => (valeurs = { ...valeurs, [champ.key]: event.currentTarget.value })}
									type={champ.secret ? 'password' : 'text'}
									autocomplete="off"
									placeholder={champ.isSet ? 'Déjà enregistré — laisser vide pour conserver' : ''}
									class="mt-1.5 w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900"
								/>
							</div>
						{/each}
					</div>
				{/if}

				{#if modeles.length}
					<div class="mt-4">
						<label class="text-xs font-medium" for="outil-modele">Modèle</label>
						<select id="outil-modele" bind:value={modele} class="mt-1.5 w-full rounded-xl border border-gray-200 px-3.5 py-2.5 text-sm dark:border-gray-800 dark:bg-gray-900">
							{#each modeles as item}<option value={item}>{item}</option>{/each}
						</select>
					</div>
				{/if}
			{/if}

			{#if messageAction}
				<div class="mt-4 rounded-xl border px-3 py-2 text-xs {messageAction.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/20 dark:text-emerald-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300'}">{messageAction.texte}</div>
			{/if}

			<div class="mt-5 flex justify-end gap-2">
				<button type="button" class="rounded-lg bg-gray-100 px-3 py-2 text-xs dark:bg-gray-850" on:click={() => (showSelection = false)}>Annuler</button>
				<button type="button" disabled={!configurationChargee || actionEnCours.has(selection.id)} class="btn-premium rounded-lg bg-gray-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-40 dark:bg-white dark:text-gray-900" on:click={enregistrer}>
					{actionEnCours.has(selection.id) ? 'Enregistrement…' : 'Enregistrer et activer'}
				</button>
			</div>
		</div>
	{/if}
</Modal>
