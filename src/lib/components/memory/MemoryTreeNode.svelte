<script lang="ts">
	// Nœud d'arbre du coffre (récursif, comme Obsidian) : dossier repliable OU ligne de note.
	// Composant dédié → la réactivité du dépliage (openState / expandedFull passés en props) est fiable.
	import type { MemoryNode } from '$lib/apis/memory';
	import Self from './MemoryTreeNode.svelte';

	export let node: MemoryNode;
	export let depth = 0;
	export let openState: Record<string, boolean>;
	export let expandedFull: Record<string, boolean>;
	export let noteCap = 40;
	export let friendlyFolder: (name: string) => string;
	export let onOpen: (node: MemoryNode) => void;
	export let onDelete: (node: MemoryNode) => void;
	export let onToggle: (path: string, depth: number) => void;
	export let onShowAll: (path: string) => void;

	$: children = node.children ?? [];
	$: folders = children.filter((c) => c.type === 'folder');
	$: notes = children.filter((c) => c.type === 'note');

	const countNotes = (n: MemoryNode): number =>
		(n.children ?? []).reduce((sum, c) => sum + (c.type === 'note' ? 1 : countNotes(c)), 0);

	// Niveau 0 ouvert par défaut, sous-dossiers fermés (scalable) — sauf choix explicite.
	$: open = openState[node.path] ?? depth === 0;
	$: cap = expandedFull[node.path] ? Number.POSITIVE_INFINITY : noteCap;
</script>

{#if node.type === 'note'}
	<div
		class="group flex items-center gap-1.5 rounded-lg hover:bg-gray-100/70 dark:hover:bg-white/5 transition"
		style="padding-left: {depth * 16 + 6}px"
	>
		<button
			class="flex-1 min-w-0 flex items-center gap-2 py-1.5 pr-1 text-left"
			on:click={() => onOpen(node)}
		>
			<span class="shrink-0 text-gray-400 dark:text-gray-500">
				<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"
					><path d="M5 3h6l4 4v10H5V3Z" stroke-linejoin="round" /><path d="M11 3v4h4" stroke-linejoin="round" /></svg
				>
			</span>
			<span class="text-[13.5px] text-gray-800 dark:text-gray-100 truncate">{node.name}</span>
		</button>
		<button
			class="shrink-0 mr-1 p-1 rounded-md text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
			title="Supprimer"
			aria-label="Supprimer la note"
			on:click={() => onDelete(node)}
		>
			<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"
				><path d="M4 6h12M8 6V4h4v2m-6 0v10h8V6" stroke-linecap="round" stroke-linejoin="round" /></svg
			>
		</button>
	</div>
{:else}
	<div>
		<button
			class="w-full flex items-center gap-1.5 py-1.5 rounded-lg hover:bg-gray-100/70 dark:hover:bg-white/5 transition text-left"
			style="padding-left: {depth * 16 + 2}px"
			on:click={() => onToggle(node.path, depth)}
		>
			<svg
				class="w-3.5 h-3.5 shrink-0 text-gray-400 transition-transform {open ? 'rotate-90' : ''}"
				viewBox="0 0 20 20"
				fill="none"
				stroke="currentColor"
				stroke-width="2"><path d="M8 5l5 5-5 5" stroke-linecap="round" stroke-linejoin="round" /></svg
			>
			<span class="shrink-0 text-amber-500/80">
				<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"
					><path
						d="M2 5.5A1.5 1.5 0 0 1 3.5 4h4l1.5 2h7A1.5 1.5 0 0 1 17.5 7.5v7A1.5 1.5 0 0 1 16 16H3.5A1.5 1.5 0 0 1 2 14.5v-9Z"
					/></svg
				>
			</span>
			<span class="text-[13.5px] font-medium text-gray-800 dark:text-gray-100 truncate"
				>{friendlyFolder(node.name)}</span
			>
			{#if countNotes(node)}
				<span class="ml-auto pr-1 text-[11px] text-gray-400 dark:text-gray-600">{countNotes(node)}</span>
			{/if}
		</button>

		{#if open}
			{#each folders as f (f.path)}
				<Self
					node={f}
					depth={depth + 1}
					{openState}
					{expandedFull}
					{noteCap}
					{friendlyFolder}
					{onOpen}
					{onDelete}
					{onToggle}
					{onShowAll}
				/>
			{/each}
			{#each notes.slice(0, cap) as n (n.path)}
				<Self
					node={n}
					depth={depth + 1}
					{openState}
					{expandedFull}
					{noteCap}
					{friendlyFolder}
					{onOpen}
					{onDelete}
					{onToggle}
					{onShowAll}
				/>
			{/each}
			{#if notes.length > cap}
				<button
					class="text-[12px] text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 py-1.5 transition"
					style="padding-left: {(depth + 1) * 16 + 24}px"
					on:click={() => onShowAll(node.path)}
				>
					Afficher les {notes.length - noteCap} autres…
				</button>
			{/if}
		{/if}
	</div>
{/if}
