<script lang="ts">
	// Sélecteur « Déplacer vers » (alternative robuste au glisser-déposer). Extrait de
	// MemoryExplorer.svelte (finding découpe) — purement présentationnel : les options proposées
	// (racine exclue ou non, cycles évités) restent calculées par le composant racine.
	import type { MemoryNode } from '$lib/apis/memory';

	export let item: MemoryNode;
	export let options: { path: string; label: string; depth: number }[];
	export let onChoose: (dest: string) => void;
	export let onCancel: () => void;
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
	class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 backdrop-blur-[2px] p-4"
	on:click={onCancel}
>
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div
		class="w-full max-w-sm max-h-[70vh] flex flex-col rounded-2xl bg-white dark:bg-gray-900 ring-1 ring-black/10 dark:ring-white/10 shadow-2xl overflow-hidden"
		on:click|stopPropagation
	>
		<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800">
			<div class="text-sm font-semibold text-gray-900 dark:text-white">Déplacer vers…</div>
			<div class="mt-0.5 text-[12px] text-gray-500 dark:text-gray-400 truncate">
				« {item.name} »
			</div>
		</div>
		<div class="flex-1 overflow-y-auto py-1.5">
			<button
				class="w-full text-left px-4 py-2 text-[13.5px] text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5 transition flex items-center gap-2"
				on:click={() => onChoose('')}
			>
				<span class="text-gray-400">🗂️</span> Racine du coffre
			</button>
			{#each options as opt (opt.path)}
				<button
					class="w-full text-left py-2 text-[13.5px] text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5 transition flex items-center gap-2"
					style="padding-left: {opt.depth * 14 + 16}px; padding-right: 16px"
					on:click={() => onChoose(opt.path)}
				>
					<span class="shrink-0 text-amber-500/80">
						<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"
							><path
								d="M2 5.5A1.5 1.5 0 0 1 3.5 4h4l1.5 2h7A1.5 1.5 0 0 1 17.5 7.5v7A1.5 1.5 0 0 1 16 16H3.5A1.5 1.5 0 0 1 2 14.5v-9Z"
							/></svg
						>
					</span>
					<span class="truncate">{opt.label}</span>
				</button>
			{/each}
		</div>
		<div class="px-4 py-2.5 border-t border-gray-100 dark:border-gray-800 flex justify-end">
			<button
				class="px-3 py-1.5 rounded-lg text-[12.5px] text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5 transition"
				on:click={onCancel}
			>
				Annuler
			</button>
		</div>
	</div>
</div>
