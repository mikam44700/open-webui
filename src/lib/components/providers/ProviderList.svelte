<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getProviders, getActiveProvider, setActiveProvider } from '$lib/apis/providers';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProviderCard from './ProviderCard.svelte';
	import ModelSelect from './ModelSelect.svelte';
	import ProviderKeyForm from './ProviderKeyForm.svelte';

	const i18n = getContext('i18n');

	type Model = { id: string; label: string };
	type Provider = {
		id: string;
		label: string;
		logo: string;
		category: 'oauth' | 'api' | 'local' | 'other';
		state: 'active' | 'configured' | 'not_configured';
		env_key?: string | null;
		base_url?: string | null;
		models?: Model[];
	};

	// Regroupement par mode de connexion (cf. category du bridge)
	const CATEGORIES = [
		{ key: 'oauth', label: 'Connexion par compte' },
		{ key: 'api', label: 'Clé API' },
		{ key: 'local', label: 'Serveur local' },
		{ key: 'other', label: 'Autres' }
	];

	let loading = true;
	let bridgeDown = false;

	let providers: Provider[] = [];
	let active: { provider_id: string; model_id: string } | null = null;

	let search = '';
	let selected: Provider | null = null;
	let selectedModel = '';
	let applying = false;

	$: filtered = search.trim()
		? providers.filter(
				(p) =>
					p.label.toLowerCase().includes(search.toLowerCase()) ||
					p.id.toLowerCase().includes(search.toLowerCase())
			)
		: providers;

	const isBridgeDown = (err: any) => err?.error?.code === 'bridge_unreachable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const token = localStorage.token;
			const [provRes, activeRes] = await Promise.all([
				getProviders(token),
				getActiveProvider(token).catch(() => null)
			]);
			providers = provRes?.providers ?? [];
			active = activeRes;
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Échec du chargement des providers'));
			}
		} finally {
			loading = false;
		}
	};

	const onSelect = (e: CustomEvent<Provider>) => {
		const provider = e.detail;
		selected = provider;
		// pré-sélectionne le modèle actif si c'est le provider courant, sinon le premier
		selectedModel =
			active?.provider_id === provider.id
				? active.model_id
				: (provider.models?.[0]?.id ?? '');
	};

	// après enregistrement d'une clé : recharge la liste et garde le panneau ouvert à jour
	const onKeySaved = async () => {
		const id = selected?.id;
		await load();
		selected = providers.find((p) => p.id === id) ?? null;
	};

	const apply = async () => {
		if (!selected || !selectedModel) return;
		applying = true;
		try {
			await setActiveProvider(localStorage.token, selected.id, selectedModel);
			toast.success($i18n.t('Cerveau actif mis à jour (s’applique aux nouvelles conversations)'));
			selected = null;
			await load();
		} catch (err: any) {
			if (err?.error?.code === 'not_configured') {
				toast.error($i18n.t('Ce provider n’est pas configuré'));
			} else {
				toast.error($i18n.t('Échec de la mise à jour du cerveau actif'));
			}
		} finally {
			applying = false;
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-5xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<!-- T021 : état dégradé, bridge injoignable -->
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Providers est injoignable')}</div>
			<div class="text-xs text-gray-500 max-w-md">
				{$i18n.t('Le pont vers Hermes ne répond pas. Vérifie qu’il tourne, puis réessaie.')}
			</div>
			<button
				class="text-xs px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={load}
			>
				{$i18n.t('Réessayer')}
			</button>
		</div>
	{:else}
		<!-- cerveau actif courant -->
		<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">
			{#if active}
				{$i18n.t('Cerveau actif')} :
				<span class="font-medium text-gray-900 dark:text-gray-100">{active.provider_id}</span>
				/ {active.model_id}
			{:else}
				{$i18n.t('Aucun cerveau actif sélectionné')}
			{/if}
		</div>

		<!-- FR-012 : recherche providers -->
		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Rechercher un provider')}
			bind:value={search}
		/>

		{#each CATEGORIES as cat (cat.key)}
			{@const items = filtered.filter((p) => p.category === cat.key)}
			{#if items.length > 0}
				<div class="mb-5">
					<div class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2 px-0.5">
						{$i18n.t(cat.label)}
						<span class="text-gray-400">({items.length})</span>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
						{#each items as provider (provider.id)}
							<ProviderCard
								{provider}
								selected={selected?.id === provider.id}
								on:select={onSelect}
							/>
						{/each}
					</div>
				</div>
			{/if}
		{/each}

		{#if filtered.length === 0}
			<div class="text-xs text-gray-500 text-center py-8">{$i18n.t('Aucun provider trouvé')}</div>
		{/if}

		<!-- panneau du provider choisi : connexion (clé/OAuth) + choix du modèle -->
		{#if selected}
			<div class="mt-4 p-4 border border-gray-100 dark:border-gray-850 rounded-2xl">
				<div class="text-sm font-medium mb-3">{selected.label}</div>

				<!-- Connexion selon la catégorie -->
				{#if selected.category === 'oauth'}
					<div class="text-xs text-gray-500">
						{$i18n.t('Ce provider se connecte avec un compte (OAuth). Connexion bientôt disponible.')}
					</div>
				{:else if selected.category === 'api' || selected.category === 'local'}
					<ProviderKeyForm provider={selected} on:saved={onKeySaved} />
				{:else}
					<div class="text-xs text-gray-500">
						{$i18n.t('Ce provider utilise un mécanisme d’authentification externe.')}
					</div>
				{/if}

				<!-- Choix du modèle + activation (si le provider expose des modèles) -->
				{#if (selected.models?.length ?? 0) > 0}
					<div class="mt-4 pt-4 border-t border-gray-100 dark:border-gray-850">
						<div class="text-sm font-medium mb-2">
							{$i18n.t('Choisir un modèle pour')}
							{selected.label}
						</div>
						<ModelSelect
							models={selected.models ?? []}
							value={selectedModel}
							on:change={(e) => (selectedModel = e.detail)}
						/>
					</div>
				{/if}

				<div class="flex justify-end gap-2 mt-3">
					<button
						class="text-sm px-3 py-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => (selected = null)}
					>
						{$i18n.t('Annuler')}
					</button>
					{#if (selected.models?.length ?? 0) > 0}
						<button
							class="text-sm px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition disabled:opacity-50"
							disabled={!selectedModel || applying}
							on:click={apply}
						>
							{#if applying}
								<Spinner className="size-4" />
							{:else}
								{$i18n.t('Définir comme cerveau actif')}
							{/if}
						</button>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>
