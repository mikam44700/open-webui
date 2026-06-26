<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getTools, setToolEnabled } from '$lib/apis/capabilities';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
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

	// Catégories techniques masquées par défaut, révélées par le « Mode Expert ».
	const EXPERT_LABELS = new Set(['Système & Code', 'Automatisation & Intégrations', OTHER_LABEL]);
	let showExpert = false;
	// Onglet de catégorie sélectionné (navigation par sous-onglets plutôt qu'une longue page).
	let selectedLabel = '';

	// Outils regroupés par catégorie, dans l'ordre défini ci-dessus. Catégories vides masquées.
	$: groups = (() => {
		const byCat = new Map<string, Toolset[]>();
		for (const cat of CATEGORIES) byCat.set(cat.label, []);
		byCat.set(OTHER_LABEL, []);
		for (const t of toolsets) {
			const cat = CATEGORIES.find((c) => c.names.includes(t.name));
			byCat.get(cat ? cat.label : OTHER_LABEL)?.push(t);
		}
		return [...CATEGORIES.map((c) => c.label), OTHER_LABEL]
			.map((label) => ({ label, items: byCat.get(label) ?? [] }))
			.filter((g) => g.items.length > 0);
	})();

	// Onglets visibles : catégories grand public ; les techniques s'ajoutent en Mode Expert.
	$: visibleTabs = showExpert ? groups : groups.filter((g) => !EXPERT_LABELS.has(g.label));
	// Catégorie affichée : celle sélectionnée si encore visible, sinon la première.
	$: activeGroup = visibleTabs.find((g) => g.label === selectedLabel) ?? visibleTabs[0] ?? null;

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
		<!-- Titre + interrupteur Mode Expert (révèle les catégories techniques). -->
		<div class="flex items-start justify-between gap-3 mb-3">
			<div class="text-sm text-gray-600 dark:text-gray-400">
				{$i18n.t('Outils natifs de ton assistant (recherche web, terminal, navigateur…)')}
			</div>
			<label
				class="flex-none flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 cursor-pointer select-none pt-0.5"
				title={$i18n.t('Affiche les outils techniques (terminal, code, intégrations…)')}
			>
				{$i18n.t('Mode Expert')}
				<Switch state={showExpert} on:change={() => (showExpert = !showExpert)} />
			</label>
		</div>

		{#if groups.length > 0}
			<!-- Sous-onglets par catégorie : on n'affiche qu'une catégorie à la fois (page courte).
			     Ils passent à la ligne (flex-wrap) — pas de scroll horizontal. -->
			<div class="flex flex-wrap gap-1.5 mb-4">
				{#each visibleTabs as tab (tab.label)}
					{@const isExpert = EXPERT_LABELS.has(tab.label)}
					<button
						type="button"
						class="text-xs px-3 py-1.5 rounded-lg transition whitespace-nowrap {activeGroup?.label ===
						tab.label
							? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900 font-medium'
							: isExpert
								? 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400/90 hover:bg-amber-100 dark:hover:bg-amber-900/30'
								: 'bg-gray-50 text-gray-600 dark:bg-gray-850 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
						on:click={() => (selectedLabel = tab.label)}
					>
						{$i18n.t(tab.label)}
						<span class="opacity-60">({tab.items.length})</span>
					</button>
				{/each}
			</div>

			{#if activeGroup}
				{#if EXPERT_LABELS.has(activeGroup.label)}
					<div class="text-[11px] text-amber-600 dark:text-amber-400/80 mb-3 px-0.5">
						{$i18n.t('Outils puissants ou techniques — réservés aux usages avancés.')}
					</div>
				{/if}
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5 items-stretch">
					{#each activeGroup.items as toolset (toolset.name)}
						<ToolsetCard
							{toolset}
							on:toggle={() => toggle(toolset)}
							on:connect={() => openConnect(toolset)}
						/>
					{/each}
				</div>
			{/if}
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
