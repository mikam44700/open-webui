<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getTools, setToolEnabled } from '$lib/apis/capabilities';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ToolsetCard from '$lib/components/capabilities/ToolsetCard.svelte';
	import ToolConnectModal from '$lib/components/capabilities/ToolConnectModal.svelte';

	const i18n = getContext('i18n');

	type Toolset = {
		name: string;
		label: string;
		description?: string;
		tools?: string[];
		enabled: boolean;
		connection_state?: string;
		providers?: string[];
	};

	let selectedToolset: Toolset | null = null;
	let showConnectModal = false;

	const openConnect = (toolset: Toolset) => {
		selectedToolset = toolset;
		showConnectModal = true;
	};

	let loading = true;
	let bridgeDown = false;
	let toolsets: Toolset[] = [];
	let search = '';

	// Regroupement par catégorie : le bridge ne renvoie pas de catégorie, on mappe par
	// nom de toolset (source de vérité = noms natifs Hermes). Tout toolset non listé
	// retombe dans « Autres » pour qu'aucun nouvel outil Hermes ne disparaisse.
	const CATEGORIES: { label: string; names: string[] }[] = [
		{ label: 'Recherche & Web', names: ['web', 'browser', 'x_search'] },
		{ label: 'Système & Code', names: ['terminal', 'file', 'code_execution', 'computer_use'] },
		{ label: 'Multimédia & Génération', names: ['image_gen', 'video_gen', 'tts', 'vision', 'video'] },
		{ label: 'Raisonnement & Agents', names: ['moa', 'skills', 'todo', 'clarify', 'delegation'] },
		{ label: 'Mémoire & Contexte', names: ['memory', 'context_engine', 'session_search'] },
		{
			label: 'Automatisation & Intégrations',
			names: ['cronjob', 'homeassistant', 'spotify', 'discord', 'discord_admin', 'yuanbao']
		}
	];
	const OTHER_LABEL = 'Autres';

	// Catégories techniques masquées par défaut, révélées par le « Mode Expert ». Tout le reste
	// (et la recherche) reste visible : le client voit l'essentiel, l'avancé est à un clic.
	const EXPERT_LABELS = new Set(['Système & Code', 'Automatisation & Intégrations', OTHER_LABEL]);
	let showExpert = false;

	$: filtered = search.trim()
		? toolsets.filter(
				(t) =>
					t.label.toLowerCase().includes(search.toLowerCase()) ||
					t.name.toLowerCase().includes(search.toLowerCase())
			)
		: toolsets;

	// Outils filtrés regroupés par catégorie, dans l'ordre défini ci-dessus.
	// On n'affiche que les catégories non vides.
	$: groups = (() => {
		const byCat = new Map<string, Toolset[]>();
		for (const cat of CATEGORIES) byCat.set(cat.label, []);
		byCat.set(OTHER_LABEL, []);
		for (const t of filtered) {
			const cat = CATEGORIES.find((c) => c.names.includes(t.name));
			byCat.get(cat ? cat.label : OTHER_LABEL)?.push(t);
		}
		return [...CATEGORIES.map((c) => c.label), OTHER_LABEL]
			.map((label) => ({ label, items: byCat.get(label) ?? [] }))
			.filter((g) => g.items.length > 0);
	})();

	// En recherche, on montre tout (l'utilisateur cherche un outil précis). Sinon on sépare
	// les catégories « grand public » des catégories techniques (révélées par le Mode Expert).
	$: isSearching = search.trim().length > 0;
	$: standardGroups = isSearching ? groups : groups.filter((g) => !EXPERT_LABELS.has(g.label));
	$: expertGroups = isSearching ? [] : groups.filter((g) => EXPERT_LABELS.has(g.label));
	$: expertCount = expertGroups.reduce((n, g) => n + g.items.length, 0);

	const isBridgeDown = (err: any) =>
		err?.error?.code === 'bridge_unreachable' || err?.error?.code === 'hermes_unavailable';

	const load = async () => {
		loading = true;
		bridgeDown = false;
		try {
			const res = await getTools(localStorage.token);
			toolsets = res?.toolsets ?? [];
		} catch (err) {
			if (isBridgeDown(err)) {
				bridgeDown = true;
			} else {
				toast.error($i18n.t('Échec du chargement des outils'));
			}
		} finally {
			loading = false;
		}
	};

	const toggle = async (toolset: Toolset) => {
		const next = !toolset.enabled;
		// Optimiste : on bascule tout de suite, rollback en cas d'échec.
		toolsets = toolsets.map((t) => (t.name === toolset.name ? { ...t, enabled: next } : t));
		try {
			await setToolEnabled(localStorage.token, toolset.name, next);
		} catch (err) {
			toolsets = toolsets.map((t) => (t.name === toolset.name ? { ...t, enabled: !next } : t));
			toast.error($i18n.t('Impossible de modifier cet outil'));
		}
	};

	onMount(load);
</script>

<div class="w-full max-w-5xl mx-auto px-3 py-3">
	{#if loading}
		<div class="flex justify-center py-16"><Spinner className="size-6" /></div>
	{:else if bridgeDown}
		<div
			class="flex flex-col items-center justify-center text-center py-16 gap-3 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
		>
			<div class="text-sm font-medium">{$i18n.t('Le service Capacités est injoignable')}</div>
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
		<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">
			{$i18n.t('Outils natifs de ton cerveau Hermes (recherche web, terminal, navigateur…)')}
		</div>

		<input
			class="w-full text-sm bg-transparent border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-2 outline-none mb-3"
			placeholder={$i18n.t('Rechercher un outil')}
			bind:value={search}
		/>

		{#snippet groupSection(group)}
			<section>
				<h3
					class="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2 px-0.5"
				>
					{$i18n.t(group.label)}
					<span class="font-normal normal-case tracking-normal">({group.items.length})</span>
				</h3>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5 items-stretch">
					{#each group.items as toolset (toolset.name)}
						<ToolsetCard
							{toolset}
							on:toggle={() => toggle(toolset)}
							on:connect={() => openConnect(toolset)}
						/>
					{/each}
				</div>
			</section>
		{/snippet}

		{#if groups.length > 0}
			<div class="flex flex-col gap-6">
				{#each standardGroups as group (group.label)}
					{@render groupSection(group)}
				{/each}

				{#if expertGroups.length > 0}
					<div>
						<button
							type="button"
							class="w-full flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 px-3 py-2.5 rounded-xl bg-gray-50 dark:bg-gray-850 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
							on:click={() => (showExpert = !showExpert)}
						>
							<span class="font-medium"
								>{$i18n.t('Mode Expert')} · {$i18n.t('outils techniques')}
								<span class="font-normal">({expertCount})</span></span
							>
							<span aria-hidden="true">{showExpert ? '▴' : '▾'}</span>
						</button>
						{#if showExpert}
							<div class="text-[11px] text-gray-400 mt-2 mb-3 px-1">
								{$i18n.t(
									'Outils puissants ou techniques (terminal, code, intégrations…) — réservés aux usages avancés.'
								)}
							</div>
							<div class="flex flex-col gap-6 mt-3">
								{#each expertGroups as group (group.label)}
									{@render groupSection(group)}
								{/each}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{:else}
			<div
				class="flex flex-col items-center justify-center text-center py-16 gap-2 border border-dashed border-gray-200 dark:border-gray-800 rounded-2xl"
			>
				<div class="text-sm font-medium">{$i18n.t('Aucun outil')}</div>
			</div>
		{/if}
	{/if}
</div>

<ToolConnectModal
	bind:open={showConnectModal}
	toolset={selectedToolset}
	on:connected={() => {
		showConnectModal = false;
		load();
	}}
	on:disconnected={() => {
		showConnectModal = false;
		load();
	}}
	on:close={() => (showConnectModal = false)}
/>
