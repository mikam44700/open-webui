<script lang="ts">
	// Barre d'actions du coffre (nombre de notes + Nouvelle note / Nouveau dossier / Tout
	// déplier-replier / Corbeille). Extrait de MemoryExplorer.svelte (finding découpe) —
	// purement présentationnel, aucun état ni logique propre.
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import type { MemoryStatus } from '$lib/apis/memory';

	export let status: MemoryStatus | null;
	export let noteTarget: string;
	export let friendlyFolder: (name: string) => string;
	export let allExpanded: boolean;
	export let onNewNote: () => void;
	export let onNewFolder: () => void;
	export let onToggleExpandAll: () => void;
	export let onOpenTrash: () => void;
</script>

<!-- Actions du coffre. Adam, lui, incarne la bannière du haut (cf. memory/+layout.svelte)
     — une seule apparition, sinon on le voit deux fois sur le même écran. -->
<div class="mt-3 mb-3 flex items-center justify-between gap-3 px-1">
	<!-- Le total vit ici, pas dans la bannière Obsidian : celle-ci disparaît là où la synchro
	     n'est pas provisionnée, et emportait le seul compteur du coffre avec elle. -->
	<div class="min-w-0 text-xs text-gray-400 dark:text-gray-500">
		{#if status?.ok}
			{status.note_count}
			{status.note_count > 1 ? 'notes' : 'note'}
		{/if}
	</div>
	<div class="flex-none flex items-center gap-1.5">
		<Tooltip content={`Créer dans : ${friendlyFolder(noteTarget) || 'Réception'}`}>
			<button
				class="px-2.5 py-1.5 rounded-xl btn-premium bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
				on:click={onNewNote}
			>
				<Plus className="size-3" strokeWidth="2.5" />
				<div class="ml-1 text-xs">Nouvelle note</div>
			</button>
		</Tooltip>
		<Tooltip content="Nouveau dossier">
			<button
				class="p-2 rounded-xl ring-1 ring-inset ring-black/10 dark:ring-white/15 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10 transition"
				on:click={onNewFolder}
				aria-label="Nouveau dossier"
			>
				<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6">
					<path
						d="M2.5 6A1.5 1.5 0 0 1 4 4.5h3l1.5 2H16A1.5 1.5 0 0 1 17.5 8v6.5A1.5 1.5 0 0 1 16 16H4a1.5 1.5 0 0 1-1.5-1.5V6Z"
						stroke-linejoin="round"
					/>
					<path d="M10 9.5v4M8 11.5h4" stroke-linecap="round" />
				</svg>
			</button>
		</Tooltip>
		<Tooltip content={allExpanded ? 'Tout replier' : 'Tout déplier'}>
			<button
				class="p-2 rounded-xl ring-1 ring-inset ring-black/10 dark:ring-white/15 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10 transition"
				on:click={onToggleExpandAll}
				aria-label={allExpanded ? 'Tout replier' : 'Tout déplier'}
			>
				<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
					{#if allExpanded}
						<!-- chevrons vers l'intérieur = tout replier -->
						<path d="M6 5l4 4 4-4M6 15l4-4 4 4" />
					{:else}
						<!-- chevrons vers l'extérieur = tout déplier -->
						<path d="M6 8l4-4 4 4M6 12l4 4 4-4" />
					{/if}
				</svg>
			</button>
		</Tooltip>
		<Tooltip content="Corbeille">
			<button
				class="p-2 rounded-xl ring-1 ring-inset ring-black/10 dark:ring-white/15 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10 transition"
				on:click={onOpenTrash}
				aria-label="Corbeille"
			>
				<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
					<path d="M4 6h12M8 6V4h4v2m-6 0v10h8V6" />
				</svg>
			</button>
		</Tooltip>
	</div>
</div>
