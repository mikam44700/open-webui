<script lang="ts">
	// Création de dossier : saisie inline (pas de prompt natif). Extrait de MemoryExplorer.svelte
	// (finding découpe) — comportement inchangé : focus auto à l'ouverture, Entrée valide, Échap annule.
	import { onMount, tick } from 'svelte';

	// Dossier cible affiché (déjà résolu par le parent : dossier courant, sinon défaut, sinon racine).
	export let folderTarget: string;
	export let friendlyFolder: (name: string) => string;
	export let onConfirm: (name: string) => void;
	export let onCancel: () => void;

	let newFolderName = '';
	let folderInput: HTMLInputElement | null = null;

	onMount(async () => {
		await tick();
		folderInput?.focus();
	});

	const confirm = () => {
		const name = newFolderName.trim();
		if (!name) {
			onCancel();
			return;
		}
		onConfirm(name);
	};
</script>

<div
	class="mb-3 flex items-center gap-2 rounded-2xl bg-gray-50 dark:bg-white/5 ring-1 ring-inset ring-black/5 dark:ring-white/10 px-3 py-2"
>
	<span class="shrink-0 text-amber-500/80">
		<svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"
			><path
				d="M2 5.5A1.5 1.5 0 0 1 3.5 4h4l1.5 2h7A1.5 1.5 0 0 1 17.5 7.5v7A1.5 1.5 0 0 1 16 16H3.5A1.5 1.5 0 0 1 2 14.5v-9Z"
			/></svg
		>
	</span>
	<input
		bind:this={folderInput}
		bind:value={newFolderName}
		class="flex-1 min-w-0 text-sm bg-transparent outline-hidden"
		placeholder="Nom du dossier"
		on:keydown={(e) => {
			if (e.key === 'Enter') {
				e.preventDefault();
				confirm();
			} else if (e.key === 'Escape') {
				onCancel();
			}
		}}
	/>
	<span class="shrink-0 text-[11px] text-gray-400 dark:text-gray-500">
		dans {folderTarget ? friendlyFolder(folderTarget.split('/').pop() ?? '') : 'la racine'}
	</span>
	<button
		class="shrink-0 px-2.5 py-1 rounded-lg bg-black text-white dark:bg-white dark:text-black text-xs font-medium transition disabled:opacity-40"
		on:click={confirm}
		disabled={!newFolderName.trim()}
	>
		Créer
	</button>
	<button
		class="shrink-0 px-2 py-1 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-200/60 dark:hover:bg-white/10 text-xs transition"
		on:click={onCancel}
	>
		Annuler
	</button>
</div>
