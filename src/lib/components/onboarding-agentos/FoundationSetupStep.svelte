<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';

	import { getCrawl4aiStatus, getToolConnection } from '$lib/apis/capabilities';
	import ToolProviderCatalogCard from '$lib/components/integrations/ToolProviderCatalogCard.svelte';
	import ProviderList from '$lib/components/providers/ProviderList.svelte';
	import type { Provider as WebProvider } from '$lib/utils/toolConnect';
	import { providerStatus } from '$lib/utils/toolConnect';

	type BrainProvider = {
		id: string;
		label: string;
		state: 'active' | 'configured' | 'not_configured';
	};

	const dispatch = createEventDispatcher();
	const featuredSlugs = ['exa', 'brave', 'tavily'];

	let section: 'brain' | 'web' = 'brain';
	let brainLoading = true;
	let activeBrain: { provider_id: string; model_id: string } | null = null;
	let brainProviders: BrainProvider[] = [];
	let webLoading = true;
	let webProviders: WebProvider[] = [];
	let crawlReady = false;
	let crawlManaged = false;

	$: activeBrainProvider = brainProviders.find(
		(provider) => provider.id === activeBrain?.provider_id
	);
	$: brainReady = Boolean(activeBrain?.provider_id && activeBrain?.model_id);
	$: activeWebProvider =
		webProviders.find(
			(provider) =>
				provider.active === true &&
				['key-active', 'detected', 'active'].includes(providerStatus(provider))
		) ?? null;
	$: webReady = Boolean(
		activeWebProvider &&
		activeWebProvider.kind !== 'managed' &&
		activeWebProvider.slug !== 'duckduckgo'
	);
	$: featuredProviders = featuredSlugs
		.map((slug) => webProviders.find((provider) => provider.slug === slug))
		.filter(Boolean) as WebProvider[];
	$: visibleWebProviders =
		activeWebProvider && !featuredSlugs.includes(activeWebProvider.slug ?? '')
			? [activeWebProvider, ...featuredProviders]
			: featuredProviders;

	const handleBrainChanged = (
		event: CustomEvent<{
			active: { provider_id: string; model_id: string } | null;
			providers: BrainProvider[];
		}>
	) => {
		activeBrain = event.detail.active;
		brainProviders = event.detail.providers ?? [];
		brainLoading = false;
	};

	const loadWeb = async () => {
		webLoading = true;
		try {
			const [connection, crawl] = await Promise.all([
				getToolConnection(localStorage.token, 'web'),
				getCrawl4aiStatus(localStorage.token).catch(() => null)
			]);
			webProviders = connection?.providers ?? [];
			crawlReady = Boolean(crawl?.active);
			crawlManaged = Boolean(crawl?.managed);
		} finally {
			webLoading = false;
		}
	};

	const complete = () => {
		if (!brainReady || !webReady) return;
		dispatch('complete', {
			providerId: activeBrain?.provider_id,
			modelId: activeBrain?.model_id,
			webProvider: activeWebProvider?.slug
		});
	};

	onMount(loadWeb);
</script>

<section class="w-full py-8">
	<div class="mx-auto max-w-4xl text-center">
		<div class="text-xs font-semibold uppercase tracking-[0.16em] text-[#6b62f2]">
			Étape 1 · Configuration de Luna
		</div>
		<h1 class="mt-3 text-3xl font-medium tracking-[-0.03em] md:text-5xl">
			Choisissez comment Luna va comprendre votre entreprise.
		</h1>
		<p class="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
			Un cerveau IA analyse vos informations. Un moteur de recherche complète votre site avec le
			marché, les concurrents et les signaux extérieurs.
		</p>
	</div>

	<div class="mx-auto mt-8 grid max-w-5xl gap-3 sm:grid-cols-3">
		<button
			class="rounded-2xl border p-4 text-left transition {section === 'brain'
				? 'border-[#6b62f2] bg-[#6b62f2]/7'
				: 'border-black/6 bg-white dark:border-white/8 dark:bg-[#161616]'}"
			on:click={() => (section = 'brain')}
		>
			<div class="flex items-center justify-between gap-2">
				<div class="text-sm font-medium">1. Cerveau IA</div>
				<span
					class="rounded-full px-2 py-0.5 text-[11px] {brainReady
						? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
						: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'}"
				>
					{brainLoading ? 'Vérification…' : brainReady ? 'Prêt' : 'À connecter'}
				</span>
			</div>
			<div class="mt-2 text-xs leading-5 text-gray-400">
				{brainReady
					? `${activeBrainProvider?.label ?? activeBrain?.provider_id} · ${activeBrain?.model_id}`
					: 'Provider et modèle obligatoires'}
			</div>
		</button>

		<button
			class="rounded-2xl border p-4 text-left transition {section === 'web'
				? 'border-[#6b62f2] bg-[#6b62f2]/7'
				: 'border-black/6 bg-white dark:border-white/8 dark:bg-[#161616]'}"
			on:click={() => (section = 'web')}
		>
			<div class="flex items-center justify-between gap-2">
				<div class="text-sm font-medium">2. Recherche Web</div>
				<span
					class="rounded-full px-2 py-0.5 text-[11px] {webReady
						? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
						: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'}"
				>
					{webLoading ? 'Vérification…' : webReady ? 'Prête' : 'À connecter'}
				</span>
			</div>
			<div class="mt-2 text-xs leading-5 text-gray-400">
				{webReady ? activeWebProvider?.name : 'Exa, Brave Search ou Tavily'}
			</div>
		</button>

		<div
			class="rounded-2xl border border-black/6 bg-white p-4 text-left dark:border-white/8 dark:bg-[#161616]"
		>
			<div class="flex items-center justify-between gap-2">
				<div class="text-sm font-medium">3. Lecture du site</div>
				<span
					class="rounded-full px-2 py-0.5 text-[11px] {crawlReady
						? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
						: 'bg-gray-100 text-gray-500 dark:bg-gray-800'}"
				>
					{crawlReady ? 'Fournie et prête' : 'Vérification…'}
				</span>
			</div>
			<div class="mt-2 text-xs leading-5 text-gray-400">
				Crawl4AI {crawlManaged ? 'est géré par LunarIA' : 'lit les pages en profondeur'}
			</div>
		</div>
	</div>

	<div
		class="mx-auto mt-5 max-w-6xl rounded-[2rem] border border-black/6 bg-white p-4 dark:border-white/8 dark:bg-[#121212] md:p-6"
	>
		{#if section === 'brain'}
			<div class="mb-5 flex flex-wrap items-center justify-between gap-3 px-2">
				<div>
					<div class="text-lg font-medium">Connectez votre provider IA</div>
					<div class="mt-1 text-xs text-gray-400">
						Choisissez ensuite le modèle qui analysera votre entreprise.
					</div>
				</div>
				{#if brainReady}
					<button
						class="rounded-full bg-[#6b62f2] px-5 py-2.5 text-sm font-medium text-white"
						on:click={() => (section = 'web')}>Continuer vers la recherche Web</button
					>
				{/if}
			</div>
			<ProviderList
				allowedTabs={['oauth', 'api', 'local']}
				showModelPicker
				on:changed={handleBrainChanged}
			/>
		{:else}
			<div class="mb-5 px-2">
				<div class="text-lg font-medium">Choisissez votre moteur de recherche</div>
				<div class="mt-1 text-xs leading-5 text-gray-400">
					Exa est recommandé pour sa recherche sémantique. Votre clé est testée avant d’être
					conservée dans le coffre serveur.
				</div>
			</div>

			{#if webLoading}
				<div class="py-14 text-center text-sm text-gray-400">Chargement des fournisseurs…</div>
			{:else}
				<div class="grid gap-3 lg:grid-cols-3">
					{#each visibleWebProviders as provider}
						<div class:order-first={provider.slug === 'exa'} class="relative">
							{#if provider.slug === 'exa'}
								<div
									class="absolute -top-2 left-4 z-10 rounded-full bg-[#6b62f2] px-2.5 py-1 text-[10px] font-semibold text-white"
								>
									Recommandé
								</div>
							{/if}
							<ToolProviderCatalogCard toolsetName="web" {provider} on:changed={loadWeb} />
						</div>
					{/each}
				</div>
				{#if visibleWebProviders.length === 0}
					<div
						class="rounded-2xl bg-amber-50 p-4 text-sm text-amber-800 dark:bg-amber-950/25 dark:text-amber-200"
					>
						Les fournisseurs de recherche sont momentanément indisponibles.
					</div>
				{/if}
			{/if}
		{/if}
	</div>

	<div
		class="mx-auto mt-5 flex max-w-5xl flex-col items-center justify-between gap-3 rounded-2xl border border-black/6 bg-white p-4 dark:border-white/8 dark:bg-[#161616] sm:flex-row"
	>
		<div class="text-xs leading-5 text-gray-500 dark:text-gray-400">
			{#if brainReady && webReady}
				Les deux capacités sont prêtes. Confirmez-les avant de confier votre site à Luna.
			{:else}
				Il reste {Number(!brainReady) + Number(!webReady)} capacité(s) obligatoire(s) à préparer.
			{/if}
		</div>
		<button
			class="rounded-full bg-[#6b62f2] px-6 py-3 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-35"
			disabled={!brainReady || !webReady}
			on:click={complete}>Confirmer et continuer vers mon site</button
		>
	</div>
</section>
