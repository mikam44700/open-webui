<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getProviders, getActiveProvider } from '$lib/apis/providers';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProviderCard from './ProviderCard.svelte';
	import HermesStatus from './HermesStatus.svelte';

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

	// Onglets : « Agent Hermes » (état/maj) + un onglet par mode de connexion (category du bridge)
	const TABS = [
		{
			key: 'hermes',
			label: 'Moteur',
			hint: 'Vérifie que ton moteur IA est bien branché et à jour.'
		},
		{
			key: 'oauth',
			label: 'Comptes',
			hint: 'Connecte-toi avec ton compte — un clic ouvre le navigateur pour autoriser.'
		},
		{ key: 'api', label: 'Clés API', hint: 'Colle ta clé API, teste-la, puis enregistre.' },
		{ key: 'local', label: 'Local', hint: 'Indique l’adresse de ton serveur local.' },
		{ key: 'other', label: 'Autres', hint: 'Modèles IA à authentification externe (AWS, Copilot).' }
	];

	let loading = true;
	let bridgeDown = false;

	let providers: Provider[] = [];
	let active: { provider_id: string; model_id: string } | null = null;

	// Onglet par défaut : Moteur (santé du moteur), première chose que voit le dirigeant.
	let activeTab = 'hermes';

	$: filtered = providers;

	const countOf = (key: string) => filtered.filter((p) => p.category === key).length;
	$: tabItems = filtered.filter((p) => p.category === activeTab);
	$: currentTab = TABS.find((t) => t.key === activeTab) ?? TABS[0];

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
			// On reste sur l'onglet courant (Moteur par défaut) — pas de saut auto vers
			// la catégorie du cerveau actif, pour un atterrissage stable et prévisible.
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Échec du chargement des modèles IA'));
			}
		} finally {
			loading = false;
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-7xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<!-- état dégradé, bridge injoignable -->
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Modèles IA est injoignable')}</div>
			<div class="text-xs text-gray-500 max-w-md">
				{$i18n.t('Le moteur ne répond pas. Vérifie qu’il tourne, puis réessaie.')}
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

		<!-- barre d'onglets — style « puces » IDENTIQUE à celui de l'onglet Outils
		     (ToolsetList) : puce active foncée + puces grises, passe à la ligne. -->
		<div class="flex flex-wrap gap-1.5 mb-3">
			{#each TABS as tab (tab.key)}
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg transition whitespace-nowrap {activeTab === tab.key
						? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900 font-medium'
						: 'bg-gray-50 text-gray-600 dark:bg-gray-850 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					on:click={() => (activeTab = tab.key)}
				>
					{$i18n.t(tab.label)}
					{#if tab.key !== 'hermes'}<span class="opacity-60">({countOf(tab.key)})</span>{/if}
				</button>
			{/each}
		</div>

		<!-- aide de l'onglet courant (masquée pour Moteur : le bandeau santé suffit) -->
		{#if activeTab !== 'hermes'}
			<div class="text-xs text-gray-500 mb-3 px-0.5">{$i18n.t(currentTab.hint)}</div>
		{/if}

		<!-- contenu de l'onglet -->
		{#if activeTab === 'hermes'}
			<HermesStatus />
		{:else if tabItems.length > 0}
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
				{#each tabItems as provider (provider.id)}
					<ProviderCard
						{provider}
						activeModelId={active?.provider_id === provider.id ? active.model_id : ''}
						on:changed={load}
					/>
				{/each}
			</div>
		{:else}
			<div class="text-xs text-gray-500 text-center py-8">{$i18n.t('Aucun modèle IA dans cet onglet')}</div>
		{/if}
	{/if}
</div>
