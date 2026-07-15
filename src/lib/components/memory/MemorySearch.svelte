<script lang="ts">
	// Barre de recherche du coffre (serveur, FTS5) + résultats. Extrait de MemoryExplorer.svelte
	// (finding découpe) — PUREMENT présentationnel : le débounce, la requête et l'état
	// (query/searching/searchResults) restent au niveau du composant racine, qui orchestre via
	// props/events (évite un risque de perte d'état si ce composant est démonté/remonté, par
	// exemple pendant que la corbeille est ouverte).
	import Search from '$lib/components/icons/Search.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { SearchResult } from '$lib/apis/memory';

	export let query: string;
	export let searching: boolean;
	export let searchResults: SearchResult[];
	export let onInput: () => void;
	export let onClear: () => void;
	export let onOpenNote: (path: string, name: string) => void;
</script>

<!-- Barre de recherche (serveur, FTS5 — scalable). -->
<div class="py-1.5 bg-white dark:bg-gray-900 rounded-2xl border border-gray-100/60 dark:border-gray-850/40">
	<div class="px-3.5 flex items-center w-full py-0.5">
		<div class="self-center ml-1 mr-3"><Search className="size-3.5" /></div>
		<input
			class="w-full text-sm py-1.5 outline-hidden bg-transparent"
			bind:value={query}
			on:input={onInput}
			placeholder="Rechercher dans vos notes"
		/>
		{#if searching}
			<Spinner className="size-3.5" />
		{:else if query}
			<button
				class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
				on:click={onClear}
			>
				<XMark className="size-3" strokeWidth="2" />
			</button>
		{/if}
	</div>
</div>

<!-- Résultats de recherche (serveur). -->
{#if query.trim()}
	{#if searchResults.length > 0}
		<div class="mt-2.5 flex flex-col gap-1.5">
			{#each searchResults as r (r.chemin)}
				<button
					class="group w-full text-left px-3.5 py-2.5 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-700 transition"
					on:click={() => onOpenNote(r.chemin, r.titre)}
				>
					<div class="text-sm font-medium text-gray-900 dark:text-white truncate">{r.titre}</div>
					{#if r.extrait}
						<div class="mt-0.5 text-[12px] text-gray-500 dark:text-gray-400 line-clamp-2">{r.extrait}</div>
					{/if}
				</button>
			{/each}
		</div>
	{:else if !searching}
		<div class="py-16 text-center text-sm text-gray-400 dark:text-gray-600">
			Aucune note pour « {query} »
		</div>
	{/if}
{/if}
