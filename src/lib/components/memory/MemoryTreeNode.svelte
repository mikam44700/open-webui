<script lang="ts">
	// Nœud d'arbre du coffre (récursif, comme Obsidian) : dossier repliable OU ligne de note.
	// Composant dédié → la réactivité du dépliage (openState / expandedFull passés en props) est fiable.
	// Porte aussi : glisser-déposer d'une note vers un dossier, renommage inline + suppression de dossier.
	import { tick } from 'svelte';
	import type { MemoryNode } from '$lib/apis/memory';
	import type { FilingSuggestion } from '$lib/memory/suggestFiling';
	import Self from './MemoryTreeNode.svelte';

	export let node: MemoryNode;
	export let depth = 0;
	export let openState: Record<string, boolean>;
	export let expandedFull: Record<string, boolean>;
	export let noteCap = 40;
	export let friendlyFolder: (name: string) => string;
	export let isStructural: (path: string) => boolean;
	export let onOpen: (node: MemoryNode) => void;
	export let onDelete: (node: MemoryNode) => void;
	export let onToggle: (path: string, depth: number) => void;
	export let onShowAll: (path: string) => void;
	export let onMoveNote: (notePath: string, destFolder: string) => void;
	export let onRequestMove: (node: MemoryNode) => void;
	export let onRenameFolder: (node: MemoryNode, newName: string) => void;
	export let onDeleteFolder: (node: MemoryNode) => void;
	// Rangement assisté (feature 021) : suggestions de destination pour les notes de Réception.
	export let suggestions: Record<string, FilingSuggestion[]> = {};
	export let dismissed: Set<string> = new Set();
	export let onFileHere: (notePath: string, dest: string) => void = () => {};
	export let onDismiss: (notePath: string) => void = () => {};

	// Suggestions de la note courante (uniquement les notes de Réception en ont). US2 en montre plusieurs.
	$: noteSuggestions = node.type === 'note' ? (suggestions[node.path] ?? []) : [];
	$: showSuggest = noteSuggestions.length > 0 && !dismissed.has(node.path);

	$: children = node.children ?? [];
	$: folders = children.filter((c) => c.type === 'folder');
	$: notes = children.filter((c) => c.type === 'note');

	const countNotes = (n: MemoryNode): number =>
		(n.children ?? []).reduce((sum, c) => sum + (c.type === 'note' ? 1 : countNotes(c)), 0);

	// Niveau 0 ouvert par défaut, sous-dossiers fermés (scalable) — sauf choix explicite.
	$: open = openState[node.path] ?? depth === 0;
	$: cap = expandedFull[node.path] ? Number.POSITIVE_INFINITY : noteCap;
	$: protectedFolder = node.type === 'folder' && isStructural(node.path);

	// Glisser-déposer : une note est la source, un dossier est la cible.
	let dragOver = false;

	// Renommage inline du dossier (état local à ce nœud → pas de fil à travers la récursion).
	let renaming = false;
	let nameDraft = '';
	let nameInput: HTMLInputElement | null = null;

	const startRename = async () => {
		renaming = true;
		nameDraft = node.name;
		await tick();
		nameInput?.focus();
		nameInput?.select();
	};
	const commitRename = () => {
		const v = nameDraft.trim();
		renaming = false;
		if (v && v !== node.name) onRenameFolder(node, v);
	};
</script>

{#if node.type === 'note'}
	<div>
	<div
		class="group flex items-center gap-1.5 rounded-lg hover:bg-gray-100/70 dark:hover:bg-white/5 transition"
		style="padding-left: {depth * 16 + 6}px"
		draggable="true"
		on:dragstart={(e) => {
			e.dataTransfer?.setData('text/plain', node.path);
			if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
		}}
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
		<!-- Déplacer vers un dossier -->
		<button
			class="shrink-0 p-1 rounded-md text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-sky-500 hover:bg-sky-50 dark:hover:bg-sky-900/20 transition"
			title="Déplacer vers…"
			aria-label="Déplacer la note"
			on:click={() => onRequestMove(node)}
		>
			<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"
				><path d="M3 8V5.5A1.5 1.5 0 0 1 4.5 4h3l1.5 2H16a1 1 0 0 1 1 1v1M3 8h14M3 8l1 7.5A1.5 1.5 0 0 0 5.5 17h9a1.5 1.5 0 0 0 1.5-1.5L17 8" stroke-linecap="round" stroke-linejoin="round" /></svg
			>
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

	<!-- Rangement assisté (021) : Adam suggère où ranger cette note de Réception (jusqu'à 3 pistes). -->
	{#if showSuggest}
		<div class="pb-1 pt-0.5" style="padding-left: {depth * 16 + 28}px">
			<div class="flex items-center gap-1.5 flex-wrap">
				<span class="inline-flex items-center gap-1 text-[11px] text-sky-600 dark:text-sky-300">
					<svg class="w-3 h-3" viewBox="0 0 20 20" fill="currentColor"
						><path
							d="M10 2l1.6 4.4L16 8l-4.4 1.6L10 14l-1.6-4.4L4 8l4.4-1.6L10 2Zm5 9l.8 2.2L18 14l-2.2.8L15 17l-.8-2.2L12 14l2.2-.8L15 11Z"
						/></svg
					>
					Adam suggère
				</span>
				{#each noteSuggestions as sug, i (sug.folder)}
					<button
						class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full transition text-[11.5px] {i === 0
							? 'bg-sky-500/10 text-sky-700 dark:text-sky-200 ring-1 ring-inset ring-sky-500/25 hover:bg-sky-500/20 font-medium'
							: 'text-gray-500 dark:text-gray-400 ring-1 ring-inset ring-gray-200 dark:ring-white/10 hover:bg-gray-100 dark:hover:bg-white/5'}"
						title={sug.reason}
						on:click={() => onFileHere(node.path, sug.folder)}
					>
						Ranger dans « {sug.label} »
					</button>
				{/each}
				<button
					class="px-1.5 py-0.5 rounded-md text-[11px] text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-white/5 transition"
					on:click={() => onDismiss(node.path)}
				>
					Ignorer
				</button>
			</div>
			{#if noteSuggestions[0].reason}
				<div class="mt-0.5 text-[11px] italic text-gray-400 dark:text-gray-500">
					{noteSuggestions[0].reason}
				</div>
			{/if}
		</div>
	{/if}
	</div>
{:else}
	<div>
		<div
			class="group flex items-center gap-1 rounded-lg hover:bg-gray-100/70 dark:hover:bg-white/5 transition {dragOver
				? 'ring-2 ring-inset ring-sky-400 bg-sky-50/60 dark:bg-sky-900/20'
				: ''}"
			role="treeitem"
			aria-selected={open}
			tabindex="-1"
			on:dragover={(e) => {
				e.preventDefault();
				dragOver = true;
			}}
			on:dragleave={() => (dragOver = false)}
			on:drop={(e) => {
				e.preventDefault();
				dragOver = false;
				const p = e.dataTransfer?.getData('text/plain');
				if (p && p !== node.path) onMoveNote(p, node.path);
			}}
		>
			<button
				class="flex-1 min-w-0 flex items-center gap-1.5 py-1.5 text-left"
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
				{#if renaming}
					<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
					<input
						bind:this={nameInput}
						bind:value={nameDraft}
						class="flex-1 min-w-0 text-[13.5px] font-medium bg-white dark:bg-gray-900 rounded px-1 outline-hidden ring-1 ring-sky-400"
						on:click={(e) => e.stopPropagation()}
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								commitRename();
							} else if (e.key === 'Escape') {
								renaming = false;
							}
						}}
						on:blur={commitRename}
					/>
				{:else}
					<span class="text-[13.5px] font-medium text-gray-800 dark:text-gray-100 truncate"
						>{friendlyFolder(node.name)}</span
					>
					{#if countNotes(node)}
						<span class="ml-auto pr-1 text-[11px] text-gray-400 dark:text-gray-600">{countNotes(node)}</span>
					{/if}
				{/if}
			</button>

			<!-- Actions du dossier (au survol) — masquées sur les dossiers structurels PARA (protégés). -->
			{#if !protectedFolder && !renaming}
				<button
					class="shrink-0 p-1 rounded-md text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200/60 dark:hover:bg-white/10 transition"
					title="Renommer le dossier"
					aria-label="Renommer le dossier"
					on:click|stopPropagation={startRename}
				>
					<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"
						><path d="M4 13.5V16h2.5l7-7L11 6.5l-7 7ZM12.5 5l2.5 2.5" stroke-linecap="round" stroke-linejoin="round" /></svg
					>
				</button>
				<button
					class="shrink-0 mr-1 p-1 rounded-md text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
					title="Supprimer le dossier"
					aria-label="Supprimer le dossier"
					on:click|stopPropagation={() => onDeleteFolder(node)}
				>
					<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"
						><path d="M4 6h12M8 6V4h4v2m-6 0v10h8V6" stroke-linecap="round" stroke-linejoin="round" /></svg
					>
				</button>
			{/if}
		</div>

		{#if open}
			{#each folders as f (f.path)}
				<Self
					node={f}
					depth={depth + 1}
					{openState}
					{expandedFull}
					{noteCap}
					{friendlyFolder}
					{isStructural}
					{onOpen}
					{onDelete}
					{onToggle}
					{onShowAll}
					{onMoveNote}
					{onRequestMove}
					{onRenameFolder}
					{onDeleteFolder}
					{suggestions}
					{dismissed}
					{onFileHere}
					{onDismiss}
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
					{isStructural}
					{onOpen}
					{onDelete}
					{onToggle}
					{onShowAll}
					{onMoveNote}
					{onRequestMove}
					{onRenameFolder}
					{onDeleteFolder}
					{suggestions}
					{dismissed}
					{onFileHere}
					{onDismiss}
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
