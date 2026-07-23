<script lang="ts">
	import { getContext, createEventDispatcher, onMount } from 'svelte';

	import { INTEGRATION_FR, INTEGRATION_CATEGORIES } from '$lib/utils/integrationLabels';
	import { getToolConnection } from '$lib/apis/capabilities';
	import { type Provider } from '$lib/utils/toolConnect';
	import IntegrationCard from './IntegrationCard.svelte';
	import ToolProviderCatalogCard from './ToolProviderCatalogCard.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	// Modale « Parcourir les intégrations » (façon Base44) : recherche + filtre par catégorie.
	// Les connecteurs MCP ont leur propre page (onglet MCP de Capacités) — pas ici.
	export let open = false;
	export let integrations: any[] = [];
	export let initialSearch = '';

	// Fournisseurs d'IA à clé (FAL, Krea, Mistral…) présentés ICI comme des cartes de catalogue,
	// au même titre que les autres intégrations. Leur « Se connecter » branche la vraie clé du
	// toolset Hermes correspondant (image_gen / tts). Ajouter une ligne pour en proposer d'autres.
	const EXTRA_PROVIDER_CARDS = [
		{ toolset: 'image_gen', slug: 'fal' },
		{ toolset: 'image_gen', slug: 'krea' },
		{ toolset: 'tts', slug: 'mistral' }
	];
	let extras: { toolsetName: string; provider: Provider }[] = [];

	const loadExtras = async () => {
		const byToolset = new Map<string, string[]>();
		for (const e of EXTRA_PROVIDER_CARDS) {
			byToolset.set(e.toolset, [...(byToolset.get(e.toolset) ?? []), e.slug]);
		}
		const out: { toolsetName: string; provider: Provider }[] = [];
		for (const [toolsetName, slugs] of byToolset) {
			try {
				const conn = await getToolConnection(localStorage.token, toolsetName);
				const providers: Provider[] = conn?.providers ?? [];
				for (const slug of slugs) {
					const p = providers.find((pp) => pp.slug === slug);
					if (p) out.push({ toolsetName, provider: p });
				}
			} catch {
				/* toolset indisponible : on ignore, les autres cartes restent affichées */
			}
		}
		extras = out;
	};

	onMount(loadExtras);

	let search = initialSearch;
	let category = '';
	let categoryOpen = false;

	// Options du filtre (« Toutes » = pas de filtre) pour le dropdown glassmorphism custom.
	$: categoryOptions = [
		{ v: '', l: 'Toutes' },
		...INTEGRATION_CATEGORIES.map((c) => ({ v: c, l: c }))
	];
	$: categoryLabel = category || 'Toutes';

	// Lien « Demander un connecteur » (placeholder : remplacer par la vraie adresse support).
	const SUPPORT_EMAIL = 'support@agent-os.app';
	const requestMailto =
		`mailto:${SUPPORT_EMAIL}?subject=` +
		encodeURIComponent('Demande de connecteur — LunarIA') +
		'&body=' +
		encodeURIComponent('Bonjour,\n\nJ’aimerais que vous ajoutiez le connecteur suivant :\n\n');

	$: filteredApps = integrations.filter((it) => {
		const fr = INTEGRATION_FR[it.id];
		if (category && fr?.category !== category) return false;
		if (search.trim()) {
			const needle = search.trim().toLowerCase();
			const hay = `${fr?.name ?? it.id} ${fr?.desc ?? ''}`.toLowerCase();
			if (!hay.includes(needle)) return false;
		}
		return true;
	});

	// Les cartes de fournisseurs IA suivent la recherche (par nom) et ne s'affichent pas quand un
	// filtre par catégorie « app » est actif (elles ne relèvent pas de ces catégories).
	$: filteredExtras = (category ? [] : extras).filter((e) => {
		if (!search.trim()) return true;
		return e.provider.name.toLowerCase().includes(search.trim().toLowerCase());
	});

	// Regroupe les intégrations filtrées par catégorie (en-têtes visibles), dans l'ordre officiel.
	// Une catégorie inconnue (jamais censé arriver) tombe en fin de liste, jamais masquée.
	$: appGroups = (() => {
		const byCat = new Map<string, any[]>();
		for (const it of filteredApps) {
			const cat = INTEGRATION_FR[it.id]?.category || 'Autres';
			if (!byCat.has(cat)) byCat.set(cat, []);
			byCat.get(cat)!.push(it);
		}
		const ordered: { key: string; items: any[] }[] = [];
		for (const c of INTEGRATION_CATEGORIES) {
			if (byCat.has(c)) {
				ordered.push({ key: c, items: byCat.get(c)! });
				byCat.delete(c);
			}
		}
		for (const [c, list] of byCat) ordered.push({ key: c, items: list });
		return ordered;
	})();

	const close = () => {
		open = false;
	};
</script>

{#if open}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
		on:click={close}
		role="presentation"
	>
		<div
			class="w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl bg-white dark:bg-gray-900 shadow-xl"
			on:click|stopPropagation={() => (categoryOpen = false)}
			role="dialog"
			aria-modal="true"
		>
			<!-- En-tête -->
			<div class="px-5 pt-5 pb-3 border-b border-gray-200 dark:border-gray-800">
				<div class="flex items-center justify-between">
					<div class="text-base font-semibold">{$i18n.t('Parcourir les intégrations')}</div>
					<button
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500"
						on:click={close}
						aria-label={$i18n.t('Fermer')}
					>
						✕
					</button>
				</div>
			</div>

			<!-- Corps -->
			<div class="flex-1 overflow-y-auto px-5 py-4">
				<!-- filtres -->
				<div class="flex items-center gap-2 mb-4">
					<input
						class="flex-1 px-3 py-2 text-sm rounded-xl bg-gray-50 dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('Rechercher une intégration…')}
						bind:value={search}
					/>
					<!-- Filtre catégorie : dropdown custom « glassmorphism » (verre dépoli). -->
					<div class="relative flex-none">
						<button
							type="button"
							class="flex items-center gap-2 px-3.5 py-2 text-sm rounded-xl bg-gray-50/80 dark:bg-gray-850/80 border border-gray-200/60 dark:border-gray-700/60 hover:bg-gray-100/80 dark:hover:bg-gray-800/80 transition outline-none"
							on:click|stopPropagation={() => (categoryOpen = !categoryOpen)}
						>
							<span>{$i18n.t(categoryLabel)}</span>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-4 text-gray-400 transition-transform {categoryOpen ? 'rotate-180' : ''}"
							>
								<path
									fill-rule="evenodd"
									d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>

						{#if categoryOpen}
							<div
								class="absolute right-0 mt-2 z-20 min-w-[12rem] p-1.5 rounded-2xl border border-white/40 dark:border-white/10 bg-white/70 dark:bg-gray-900/60 backdrop-blur-2xl shadow-2xl ring-1 ring-black/5"
								on:click|stopPropagation
								role="listbox"
								tabindex="-1"
							>
								{#each categoryOptions as opt (opt.v)}
									<button
										type="button"
										role="option"
										aria-selected={category === opt.v}
										class="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl text-sm text-left transition hover:bg-white/70 dark:hover:bg-white/10 {category ===
										opt.v
											? 'font-medium text-gray-900 dark:text-white'
											: 'text-gray-600 dark:text-gray-300'}"
										on:click={() => {
											category = opt.v;
											categoryOpen = false;
										}}
									>
										<span>{$i18n.t(opt.l)}</span>
										{#if category === opt.v}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="size-4 text-sky-500"
											>
												<path
													fill-rule="evenodd"
													d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
													clip-rule="evenodd"
												/>
											</svg>
										{/if}
									</button>
								{/each}
							</div>
						{/if}
					</div>
				</div>

				{#if filteredApps.length > 0 || filteredExtras.length > 0}
					{#each appGroups as group (group.key)}
						<div class="mb-6">
							<div
								class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2"
							>
								{$i18n.t(group.key)}
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
								{#each group.items as integration (integration.id)}
									<IntegrationCard {integration} on:changed={() => dispatch('changed')} />
								{/each}
							</div>
						</div>
					{/each}
					{#if filteredExtras.length > 0}
						<div class="mb-6 last:mb-0">
							<div
								class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2"
							>
								{$i18n.t('Modèles d’IA & voix')}
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
								{#each filteredExtras as e (e.toolsetName + ':' + e.provider.name)}
									<ToolProviderCatalogCard
										toolsetName={e.toolsetName}
										provider={e.provider}
										on:changed={() => dispatch('changed')}
									/>
								{/each}
							</div>
						</div>
					{/if}
				{:else}
					<div class="text-xs text-gray-500 text-center py-10">
						{$i18n.t('Aucune intégration ne correspond.')}
					</div>
				{/if}
			</div>

			<!-- Footer épinglé : demander un connecteur (façon Base44). -->
			<div
				class="border-t border-gray-100 dark:border-gray-800 px-5 py-3 text-center text-sm text-gray-500"
			>
				{$i18n.t('Vous ne trouvez pas ce qu’il vous faut ?')}
				<a
					class="font-medium text-gray-900 underline underline-offset-2 hover:opacity-80 dark:text-white"
					href={requestMailto}
				>
					{$i18n.t('Demander un connecteur')}
				</a>
			</div>
		</div>
	</div>
{/if}
