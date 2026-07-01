<script lang="ts">
	// Onglet « Ce qu'il a retenu » (feature 017) : liste MEMORY.md (add/edit/delete).
	// Suppression TOUJOURS confirmée (garde-fou). Surtout rempli par l'assistant lui-même.
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { getEntries, addEntry, updateEntry, removeEntry } from '$lib/apis/memory';
	import type { MemoryEntry } from '$lib/apis/memory';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let loaded = false;
	let loadError = false;
	let entries: MemoryEntry[] = [];

	let adding = false;
	let newContent = '';
	let editingIndex: number | null = null;
	let editContent = '';
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

	const doUpdate = async () => {
		if (editingIndex === null) return;
		busy = true;
		try {
			applyResult(await updateEntry(localStorage.token, editingIndex, editContent.trim()));
			editingIndex = null;
			editContent = '';
		} catch (e: any) {
			toast.error(e?.error?.message ?? $i18n.t('Impossible de modifier.'));
		} finally {
			busy = false;
		}
	};

	const doDelete = async (index: number) => {
		busy = true;
		try {
			applyResult(await removeEntry(localStorage.token, index));
			confirmDelete = null;
		} catch (e: any) {
			toast.error(e?.error?.message ?? $i18n.t('Impossible de supprimer.'));
		} finally {
			busy = false;
		}
	};
</script>

<div class="w-full py-4">
	{#if !loaded}
		<div class="flex justify-center py-16"><Spinner /></div>
	{:else if loadError}
		<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-6 text-sm text-gray-600 dark:text-gray-300">
			{$i18n.t("Impossible de lire ce que l'assistant a retenu pour le moment.")}
			<button class="ml-2 underline" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else}
		<div class="mb-4 flex items-center justify-end">
			<button
				class="shrink-0 px-3 py-1.5 rounded-lg text-xs bg-gray-900 dark:bg-white text-white dark:text-gray-900 transition"
				on:click={() => (adding = !adding)}
			>
				{$i18n.t('Ajouter un souvenir')}
			</button>
		</div>

		{#if adding}
			<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-3 mb-3">
				<textarea
					class="w-full h-32 bg-transparent text-sm leading-relaxed resize-y outline-none"
					bind:value={newContent}
					placeholder={$i18n.t('Ex. : Je préfère être appelé le matin.')}
					spellcheck="false"
				></textarea>
				<div class="flex justify-end gap-2 mt-2">
					<button class="px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-800" on:click={() => { adding = false; newContent = ''; }}>
						{$i18n.t('Annuler')}
					</button>
					<button class="px-3 py-1.5 rounded-lg text-xs bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40" disabled={!newContent.trim() || busy} on:click={doAdd}>
						{$i18n.t('Enregistrer')}
					</button>
				</div>
			</div>
		{/if}

		{#if entries.length === 0}
			<div class="rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 p-8 text-center">
				<p class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t("Rien pour l'instant.")}</p>
				<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
					{$i18n.t("Ce tiroir se remplit tout seul au fil de vos conversations.")}
				</p>
			</div>
		{:else}
			<div class="flex flex-col gap-2">
				{#each entries as entry (entry.index)}
					<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-3">
						{#if editingIndex === entry.index}
							<textarea class="w-full h-32 bg-transparent text-sm leading-relaxed resize-y outline-none" bind:value={editContent} spellcheck="false"></textarea>
							<div class="flex justify-end gap-2 mt-2">
								<button class="px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-800" on:click={() => (editingIndex = null)}>
									{$i18n.t('Annuler')}
								</button>
								<button class="px-3 py-1.5 rounded-lg text-xs bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40" disabled={busy} on:click={doUpdate}>
									{$i18n.t('Enregistrer')}
								</button>
							</div>
						{:else}
							<div class="flex items-start justify-between gap-3">
								<div class="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap flex-1">{entry.content}</div>
								<div class="flex items-center gap-1 shrink-0">
									{#if confirmDelete === entry.index}
										<span class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Supprimer ?')}</span>
										<button class="px-2 py-1 rounded text-xs text-red-600" disabled={busy} on:click={() => doDelete(entry.index)}>{$i18n.t('Oui')}</button>
										<button class="px-2 py-1 rounded text-xs" on:click={() => (confirmDelete = null)}>{$i18n.t('Non')}</button>
									{:else}
										<button class="px-2 py-1 rounded text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white" on:click={() => { editingIndex = entry.index; editContent = entry.content; }}>
											{$i18n.t('Modifier')}
										</button>
										<button class="px-2 py-1 rounded text-xs text-gray-400 hover:text-red-600" on:click={() => (confirmDelete = entry.index)}>
											{$i18n.t('Supprimer')}
										</button>
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
