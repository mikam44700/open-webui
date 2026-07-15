<script lang="ts">
	// Onglet « Ce qu'il a retenu » (feature 017) : liste MEMORY.md (add/edit/delete).
	// Suppression TOUJOURS confirmée (garde-fou). Surtout rempli par l'assistant lui-même.
	// UI premium : empty state interactif, cartes hover-lift, actions révélées au survol, skeleton.
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { getEntries, addEntry, updateEntry, removeEntry } from '$lib/apis/memory';
	import type { MemoryEntry } from '$lib/apis/memory';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let loaded = false;
	let loadError = false;
	let entries: MemoryEntry[] = [];

	let adding = false;
	let newContent = '';
	let editingIndex: number | null = null;
	let editContent = '';
	let editingExpected = ''; // contenu vu au dernier chargement, pour la garde de concurrence
	let confirmDelete: number | null = null;
	let busy = false;

	const load = async () => {
		loaded = false;
		loadError = false;
		try {
			const data = await getEntries(localStorage.token);
			entries = data.entries ?? [];
		} catch (e) {
			loadError = true;
		} finally {
			loaded = true;
		}
	};

	onMount(load);

	const applyResult = (data: { entries: MemoryEntry[] }) => {
		entries = data.entries ?? [];
	};

	const openAdd = () => {
		adding = true;
		newContent = '';
	};

	const doAdd = async () => {
		if (!newContent.trim()) return;
		busy = true;
		try {
			applyResult(await addEntry(localStorage.token, newContent.trim()));
			newContent = '';
			adding = false;
		} catch (e: any) {
			toast.error(e?.error?.message ?? $i18n.t("Impossible d'ajouter."));
		} finally {
			busy = false;
		}
	};

	// L'assistant écrit aussi dans MEMORY.md pendant que le dirigeant a l'écran ouvert : si
	// l'entrée visée a changé depuis le dernier chargement, le serveur répond 409
	// (entry_conflict) plutôt que d'écraser/supprimer la mauvaise entrée. On referme l'édition
	// en cours et on recharge la liste pour repartir d'un état sûr.
	const isConflict = (e: any) => e?.error?.code === 'entry_conflict';

	const handleConflict = async (e: any, fallback: string) => {
		toast.error(e?.error?.message ?? fallback);
		editingIndex = null;
		editContent = '';
		confirmDelete = null;
		await load();
	};

	const doUpdate = async () => {
		if (editingIndex === null) return;
		busy = true;
		try {
			applyResult(
				await updateEntry(localStorage.token, editingIndex, editContent.trim(), editingExpected)
			);
			editingIndex = null;
			editContent = '';
		} catch (e: any) {
			if (isConflict(e)) {
				await handleConflict(e, $i18n.t('Ce souvenir a changé, réessayez.'));
			} else {
				toast.error(e?.error?.message ?? $i18n.t('Impossible de modifier.'));
			}
		} finally {
			busy = false;
		}
	};

	const doDelete = async (index: number) => {
		const expected = entries.find((e) => e.index === index)?.content;
		busy = true;
		try {
			applyResult(await removeEntry(localStorage.token, index, expected));
			confirmDelete = null;
		} catch (e: any) {
			if (isConflict(e)) {
				await handleConflict(e, $i18n.t('Ce souvenir a changé, réessayez.'));
			} else {
				toast.error(e?.error?.message ?? $i18n.t('Impossible de supprimer.'));
			}
		} finally {
			busy = false;
		}
	};
</script>

<div class="w-full py-5">
	{#if !loaded}
		<div class="animate-pulse">
			<div class="h-9 w-40 rounded-lg bg-gray-100 dark:bg-gray-800 ml-auto mb-3"></div>
			<div class="flex flex-col gap-2.5">
				{#each Array(3) as _}
					<div class="h-16 rounded-2xl bg-gray-100 dark:bg-gray-800"></div>
				{/each}
			</div>
		</div>
	{:else if loadError}
		<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-6 text-sm text-gray-600 dark:text-gray-300">
			{$i18n.t("Impossible de lire ce que l'assistant a retenu pour le moment.")}
			<button class="ml-2 font-medium underline underline-offset-2" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else}
		{#if entries.length > 0 || adding}
			<div class="mb-3 flex items-center justify-end">
				<button
					class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 transition"
					on:click={openAdd}
				>
					<svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path d="M10 4a1 1 0 0 1 1 1v4h4a1 1 0 1 1 0 2h-4v4a1 1 0 1 1-2 0v-4H5a1 1 0 1 1 0-2h4V5a1 1 0 0 1 1-1Z"/></svg>
					{$i18n.t('Ajouter un souvenir')}
				</button>
			</div>
		{/if}

		{#if adding}
			<div class="rounded-2xl border border-gray-300 dark:border-gray-700 p-3.5 mb-2.5 focus-within:border-gray-400 dark:focus-within:border-gray-600 focus-within:ring-4 focus-within:ring-gray-100 dark:focus-within:ring-gray-800/50 transition">
				<textarea
					class="w-full h-28 bg-transparent text-sm leading-relaxed resize-y outline-none"
					bind:value={newContent}
					placeholder={$i18n.t('Ex. : Je préfère être appelé le matin.')}
					spellcheck="false"
				></textarea>
				<div class="flex justify-end gap-2 mt-2">
					<button class="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition" on:click={() => { adding = false; newContent = ''; }}>
						{$i18n.t('Annuler')}
					</button>
					<button class="px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40 hover:opacity-90 transition" disabled={!newContent.trim() || busy} on:click={doAdd}>
						{$i18n.t('Enregistrer')}
					</button>
				</div>
			</div>
		{/if}

		{#if entries.length === 0 && !adding}
			<!-- Empty state interactif : on peut agir directement -->
			<button
				class="group w-full rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 p-12 text-center hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-50/50 dark:hover:bg-gray-850/30 transition"
				on:click={openAdd}
			>
				<span class="mx-auto mb-3 flex items-center justify-center w-11 h-11 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-400 group-hover:bg-gray-900 group-hover:text-white dark:group-hover:bg-white dark:group-hover:text-gray-900 transition">
					<svg class="w-5 h-5" viewBox="0 0 20 20" fill="currentColor"><path d="M10 4a1 1 0 0 1 1 1v4h4a1 1 0 1 1 0 2h-4v4a1 1 0 1 1-2 0v-4H5a1 1 0 1 1 0-2h4V5a1 1 0 0 1 1-1Z"/></svg>
				</span>
				<p class="text-sm font-medium text-gray-700 dark:text-gray-200">{$i18n.t('Ajoutez un premier souvenir')}</p>
				<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
					{$i18n.t('…ou laissez votre assistant remplir ce tiroir tout seul au fil de vos conversations.')}
				</p>
			</button>
		{:else}
			<div class="flex flex-col gap-2.5">
				{#each entries as entry (entry.index)}
					<div class="group rounded-2xl border border-gray-200 dark:border-gray-800 p-3.5 transition-all duration-200 {editingIndex === entry.index ? '' : 'hover:-translate-y-0.5 hover:shadow-[0_2px_10px_rgba(0,0,0,0.05)] hover:border-gray-300 dark:hover:border-gray-700'}">
						{#if editingIndex === entry.index}
							<textarea class="w-full h-24 bg-transparent text-sm leading-relaxed resize-y outline-none" bind:value={editContent} spellcheck="false"></textarea>
							<div class="flex justify-end gap-2 mt-2">
								<button class="px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition" on:click={() => (editingIndex = null)}>
									{$i18n.t('Annuler')}
								</button>
								<button class="px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40 hover:opacity-90 transition" disabled={busy} on:click={doUpdate}>
									{$i18n.t('Enregistrer')}
								</button>
							</div>
						{:else}
							<div class="flex items-start justify-between gap-3">
								<div class="text-sm text-gray-800 dark:text-gray-100 leading-relaxed whitespace-pre-wrap flex-1">{entry.content}</div>
								<div class="flex items-center gap-0.5 shrink-0">
									{#if confirmDelete === entry.index}
										<span class="text-xs text-gray-500 dark:text-gray-400 mr-1">{$i18n.t('Supprimer ?')}</span>
										<button class="px-2 py-1 rounded-md text-xs font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40" disabled={busy} on:click={() => doDelete(entry.index)}>{$i18n.t('Oui')}</button>
										<button class="px-2 py-1 rounded-md text-xs font-medium hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => (confirmDelete = null)}>{$i18n.t('Non')}</button>
									{:else}
										<div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition">
											<button class="p-1.5 rounded-md text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-850 transition" title={$i18n.t('Modifier')} on:click={() => { editingIndex = entry.index; editContent = entry.content; editingExpected = entry.content; }}>
												<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 13.5V16h2.5l7.4-7.4-2.5-2.5L4 13.5Z" stroke-linejoin="round"/><path d="m12.6 4.9 2.5 2.5" stroke-linecap="round"/></svg>
											</button>
											<button class="p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition" title={$i18n.t('Supprimer')} on:click={() => (confirmDelete = entry.index)}>
												<svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 6h12M8.5 6V4.5h3V6M6 6l.6 9.5h6.8L14 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
											</button>
										</div>
									{/if}
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>
