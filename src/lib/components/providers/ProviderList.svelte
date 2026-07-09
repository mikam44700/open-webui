<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getProviders, getActiveProvider } from '$lib/apis/providers';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ProviderCard from './ProviderCard.svelte';
	import MoaConfig from './MoaConfig.svelte';
	import HermesStatus from './HermesStatus.svelte';
	import {
		groupProviders,
		MULTIAGENT_IDS,
		isExpertProvider,
		isHiddenProvider
	} from '$lib/catalog/provider-taxonomy';
	import { getProviderName } from '$lib/catalog/provider-info';
	import { expertMode } from '$lib/stores';

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
		{
			key: 'multiagent',
			label: 'Modèles IA combinés',
			hint: 'Plusieurs modèles IA qui réfléchissent ensemble pour une meilleure réponse.'
		},
		{ key: 'local', label: 'Local', hint: 'Indique l’adresse de ton serveur local.' },
		{ key: 'other', label: 'Autres', hint: 'Modèles IA à authentification externe (AWS, Copilot).' }
	];

	let loading = true;
	let bridgeDown = false;

	let providers: Provider[] = [];
	let active: { provider_id: string; model_id: string } | null = null;

	// Onglet par défaut : Moteur (santé du moteur), première chose que voit le dirigeant.
	let activeTab = 'hermes';

	// Onglets réservés au mode Expert (Réglages avancés) : masqués au dirigeant par défaut.
	const EXPERT_TABS = new Set<string>(['multiagent', 'other']);

	$: filtered = providers;

	// Les fournisseurs multi-agents (Sakana, MoA) ont leur propre onglet « Cerveaux
	// combinés » et sont EXCLUS de « Clés API » (sinon doublon).
	const inMulti = (p: Provider) => MULTIAGENT_IDS.has(p.id);
	// Un fournisseur « Expert » n'est visible que si le mode Expert est actif (réactif).
	// Un fournisseur « masqué » (service mort/discontinué) n'apparaît jamais, même en Expert.
	$: canShow = (p: Provider) => !isHiddenProvider(p.id) && ($expertMode || !isExpertProvider(p.id));

	// Modèle IA actif : y a-t-il au moins un fournisseur connecté ? + son nom LISIBLE
	// (le label du fournisseur, jamais le slug technique « auto » / « openai-codex »).
	$: brainConnected = providers.some((p) => p.state !== 'not_configured');
	$: activeProviderLabel = (() => {
		const p = providers.find((pp) => pp.id === active?.provider_id);
		return p ? getProviderName(p.id, p.label) : (active?.provider_id ?? '');
	})();

	// Onglets visibles : on retire « Cerveaux combinés » et « Autres » hors mode Expert.
	$: visibleTabs = $expertMode ? TABS : TABS.filter((t) => !EXPERT_TABS.has(t.key));
	// Filet de sécurité : si on quitte le mode Expert alors qu'un onglet Expert est ouvert,
	// on retombe sur « Moteur » (jamais coincé sur un onglet devenu invisible).
	$: if (!$expertMode && EXPERT_TABS.has(activeTab)) activeTab = 'hermes';

	// Compteurs par onglet (réactifs au mode Expert via canShow).
	$: counts = {
		oauth: filtered.filter((p) => p.category === 'oauth' && canShow(p)).length,
		api: filtered.filter((p) => p.category === 'api' && !inMulti(p) && canShow(p)).length,
		multiagent: filtered.filter(inMulti).length,
		local: filtered.filter((p) => p.category === 'local' && canShow(p)).length,
		other: filtered.filter((p) => p.category === 'other' && canShow(p)).length
	} as Record<string, number>;

	$: tabItems =
		activeTab === 'multiagent'
			? filtered.filter(inMulti)
			: activeTab === 'api'
				? filtered.filter((p) => p.category === 'api' && !inMulti(p) && canShow(p))
				: filtered.filter((p) => p.category === activeTab && canShow(p));
	$: currentTab = TABS.find((t) => t.key === activeTab) ?? TABS[0];
	// Connectés (actifs ou déjà configurés) — remontés EN HAUT de chaque onglet fournisseurs.
	$: connectedItems = tabItems.filter((p) => p.state !== 'not_configured');
	$: connectedIds = new Set(connectedItems.map((p) => p.id));
	// « À découvrir » = le reste, non encore connecté (évite le doublon avec la section du haut).
	$: discoverItems = tabItems.filter((p) => !connectedIds.has(p.id));
	// Onglet « Clés API » : on range les fournisseurs À DÉCOUVRIR en sections (Les grands noms,
	// Une seule clé plein de modèles, Plateformes d'hébergement, Modèles chinois, Sur-mesure).
	// Les autres onglets restent en grille plate (peu d'items).
	$: apiGroups = activeTab === 'api' ? groupProviders(discoverItems) : [];

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
			{#if brainConnected && active}
				{$i18n.t('Modèle IA actif')} :
				<span class="font-medium text-gray-900 dark:text-gray-100">{activeProviderLabel}</span>
			{:else}
				{$i18n.t('Aucun modèle IA connecté')}
			{/if}
		</div>

		<!-- barre d'onglets — style « puces » IDENTIQUE à celui de l'onglet Outils
		     (ToolsetList) : puce active foncée + puces grises, passe à la ligne. -->
		<div class="flex flex-wrap gap-1.5 mb-3">
			{#each visibleTabs as tab (tab.key)}
				<button
					type="button"
					class="text-xs px-3 py-1.5 rounded-lg transition whitespace-nowrap {activeTab === tab.key
						? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900 font-medium'
						: 'bg-gray-50 text-gray-600 dark:bg-gray-850 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
					on:click={() => (activeTab = tab.key)}
				>
					{$i18n.t(tab.label)}
					{#if tab.key !== 'hermes'}<span class="opacity-60">({counts[tab.key]})</span>{/if}
				</button>
			{/each}
		</div>

		<!-- aide de l'onglet courant (masquée pour Moteur + Cerveaux combinés : encart dédié) -->
		{#if activeTab !== 'hermes' && activeTab !== 'multiagent'}
			<div class="text-xs text-gray-500 mb-3 px-0.5">{$i18n.t(currentTab.hint)}</div>
		{/if}

		<!-- Encart pédagogique « Cerveaux combinés » -->
		{#if activeTab === 'multiagent'}
			<div
				class="mb-4 rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/60 dark:bg-gray-850/40 p-4"
			>
				<div class="text-sm font-medium mb-1">
					{$i18n.t('Plusieurs modèles IA, une meilleure réponse')}
				</div>
				<p class="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
					{$i18n.t(
						'Au lieu d’un seul modèle, plusieurs IA réfléchissent en parallèle puis un « chef de synthèse » combine le meilleur de chacune. Résultat souvent plus fiable — mais plus lent et plus coûteux (plusieurs modèles travaillent). À réserver aux décisions importantes, pas au quotidien.'
					)}
				</p>
				<ul class="mt-2 flex flex-col gap-1">
					<li class="flex items-start gap-1.5 text-xs text-gray-600 dark:text-gray-400">
						<span class="flex-none mt-1 size-1 rounded-full bg-gray-400 dark:bg-gray-600"></span>
						<span
							>{$i18n.t(
								'Sakana Fugu : le plus simple — tu entres ta clé, la combinaison est gérée pour toi.'
							)}</span
						>
					</li>
					<li class="flex items-start gap-1.5 text-xs text-gray-600 dark:text-gray-400">
						<span class="flex-none mt-1 size-1 rounded-full bg-gray-400 dark:bg-gray-600"></span>
						<span
							>{$i18n.t(
								'Mixture of Agents : tu choisis toi-même quels modèles IA (déjà connectés) combiner.'
							)}</span
						>
					</li>
				</ul>
			</div>
		{/if}

		<!-- contenu de l'onglet -->
		{#if activeTab === 'hermes'}
			<HermesStatus />
		{:else if activeTab === 'multiagent'}
			<!-- Modèles IA combinés : grille plate avec carte MoA dédiée (inchangé). -->
			{#if tabItems.length > 0}
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
					{#each tabItems as provider (provider.id)}
						{#if provider.id === 'moa'}
							<!-- Mixture of Agents : carte de configuration dédiée (proposeurs + agrégateur). -->
							<MoaConfig {provider} {providers} on:changed={load} />
						{:else}
							<ProviderCard
								{provider}
								activeModelId={active?.provider_id === provider.id ? active.model_id : ''}
								on:changed={load}
							/>
						{/if}
					{/each}
				</div>
			{:else}
				<div class="text-xs text-gray-500 text-center py-8">{$i18n.t('Aucun modèle IA dans cet onglet')}</div>
			{/if}
		{:else}
			<!-- Onglets fournisseurs (Comptes / Clés API / Local / Autres) : connectés EN HAUT + à découvrir. -->
			{#if connectedItems.length > 0}
				<div class="mb-6">
					<div
						class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2 px-0.5"
					>
						{$i18n.t('Connectés')}
						<span class="opacity-60">({connectedItems.length})</span>
					</div>
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
						{#each connectedItems as provider (provider.id)}
							<ProviderCard
								{provider}
								activeModelId={active?.provider_id === provider.id ? active.model_id : ''}
								on:changed={load}
							/>
						{/each}
					</div>
				</div>
			{/if}

			{#if activeTab === 'api'}
				<!-- À découvrir : rangés par sections (familiarité + fonction). -->
				<div class="flex flex-col gap-6">
					{#each apiGroups as group (group.key)}
						<div>
							<div
								class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2 px-0.5"
							>
								{$i18n.t(group.label)}
								<span class="opacity-60">({group.items.length})</span>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
								{#each group.items as provider (provider.id)}
									<ProviderCard
										{provider}
										activeModelId={active?.provider_id === provider.id ? active.model_id : ''}
										on:changed={load}
									/>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			{:else if discoverItems.length > 0}
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
					{#each discoverItems as provider (provider.id)}
						<ProviderCard
							{provider}
							activeModelId={active?.provider_id === provider.id ? active.model_id : ''}
							on:changed={load}
						/>
					{/each}
				</div>
			{/if}

			{#if connectedItems.length === 0 && discoverItems.length === 0}
				<div class="text-xs text-gray-500 text-center py-8">{$i18n.t('Aucun modèle IA dans cet onglet')}</div>
			{/if}
		{/if}
	{/if}
</div>
