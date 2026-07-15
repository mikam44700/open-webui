<script lang="ts">
	// Vue éditeur d'une note du coffre. Extrait de MemoryExplorer.svelte (finding découpe) —
	// PUREMENT présentationnel : le débounce de sauvegarde, le renommage et la suppression restent
	// au niveau du composant racine (le flush à la navigation / au démontage dépend de leur
	// ordonnancement exact — les déplacer ici aurait risqué un changement de comportement).
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import type { MemoryNode } from '$lib/apis/memory';
	import type { Editor } from '@tiptap/core';

	export let loadingNote: boolean;
	export let selectedNode: MemoryNode | null;
	export let titleDraft: string;
	export let saveState: 'idle' | 'saving' | 'saved';
	export let noteModified: number | null;
	export let currentMd: string;
	export let formatModified: (epoch: number | null) => string;
	export let onBack: () => void | Promise<void>;
	export let onCommitRename: () => void | Promise<void>;
	export let onDelete: () => void | Promise<void>;
	export let onChange: (content: { md?: string }) => void;

	let titleInput: HTMLInputElement | null = null;
	let inputElement: RichTextInput | null = null;
	let editor: Editor | null = null;

	// Appelé par le parent (via bind:this) juste après la création d'une note : le titre est
	// prêt à être renommé tout de suite.
	export function focusTitle(): void {
		titleInput?.focus();
		titleInput?.select();
	}
</script>

<div class="relative flex-1 w-full h-full flex justify-center pt-[11px]" id="memory-editor">
	{#if loadingNote}
		<div class="absolute top-0 bottom-0 left-0 right-0 flex">
			<div class="m-auto"><Spinner className="size-5" /></div>
		</div>
	{:else}
		<div class="w-full flex flex-col">
			<!-- Barre supérieure : retour + titre + indicateur sauvegarde -->
			<div class="shrink-0 w-full flex justify-between items-center px-3.5 mb-1.5">
				<div class="w-full min-w-0 flex items-center gap-2">
					<!-- Bouton retour -->
					<Tooltip content="Retour à la liste">
						<button
							class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition p-1.5 shrink-0"
							on:click={onBack}
						>
							<ChevronLeft className="size-4" />
						</button>
					</Tooltip>

					<!-- Titre de la note — éditable (renommage à la validation / perte de focus). -->
					<input
						bind:this={titleInput}
						class="w-full text-2xl font-medium bg-transparent outline-hidden"
						type="text"
						bind:value={titleDraft}
						placeholder="Sans titre"
						on:blur={onCommitRename}
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								(e.currentTarget as HTMLInputElement).blur();
							}
						}}
					/>
				</div>

				<div class="shrink-0 flex items-center gap-1.5 pr-1">
					<!-- Indicateur de sauvegarde / date de dernière modif -->
					<div class="text-xs text-gray-500 dark:text-gray-500">
						{#if saveState === 'saving'}
							Enregistrement…
						{:else if saveState === 'saved'}
							Enregistré
						{:else if noteModified}
							Modifié le {formatModified(noteModified)}
						{/if}
					</div>
					<!-- Supprimer la note (corbeille récupérable) -->
					<Tooltip content="Supprimer">
						<button
							class="cursor-pointer flex rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition p-1.5"
							on:click={onDelete}
						>
							<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 6h12M8 6V4h4v2m-6 0v10h8V6" stroke-linecap="round" stroke-linejoin="round" /></svg>
						</button>
					</Tooltip>
				</div>
			</div>

			<!-- Zone d'édition principale -->
			<div
				class="flex-1 w-full h-full overflow-auto px-3.5 relative"
				id="memory-content-container"
			>
				{#key selectedNode?.path}
					<RichTextInput
						bind:this={inputElement}
						bind:editor
						id={`memory-${selectedNode?.path ?? 'note'}`}
						className="input-prose-sm px-0.5 h-[calc(100%-2rem)]"
						value={currentMd}
						dragHandle={true}
						link={true}
						image={true}
						placeholder="Écrivez quelque chose…"
						onChange={(content) => {
							onChange(content);
						}}
					/>
				{/key}
			</div>
		</div>
	{/if}
</div>
