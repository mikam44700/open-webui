<script lang="ts">
	import type { MemoireEntry } from '$lib/apis/memoire';

	export let entry: MemoireEntry;
	export let selectedPath: string | null = null;
	export let onSelect: (entry: MemoireEntry) => void;
	export let depth = 0;

	let open = depth === 0;
</script>

{#if entry.type === 'dossier'}
	<button
		class="w-full flex items-center gap-1.5 px-2 py-1 rounded-lg text-left text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
		style="padding-left: {0.5 + depth * 0.75}rem"
		on:click={() => (open = !open)}
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			stroke-width="1.5"
			stroke="currentColor"
			class="size-3.5 shrink-0 transition-transform {open ? 'rotate-90' : ''}"
		>
			<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
		</svg>
		<span class="truncate font-medium">{entry.name}</span>
	</button>
	{#if open && entry.children}
		{#each entry.children as child (child.path)}
			<svelte:self entry={child} {selectedPath} {onSelect} depth={depth + 1} />
		{/each}
	{/if}
{:else}
	<button
		class="w-full flex items-center gap-1.5 px-2 py-1 rounded-lg text-left text-sm transition {selectedPath ===
		entry.path
			? 'bg-violet-50 dark:bg-gray-850 text-violet-600 dark:text-violet-400'
			: 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850'}"
		style="padding-left: {0.5 + depth * 0.75}rem"
		on:click={() => onSelect(entry)}
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			stroke-width="1.5"
			stroke="currentColor"
			class="size-3.5 shrink-0"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
			/>
		</svg>
		<span class="truncate">{entry.name}</span>
	</button>
{/if}
