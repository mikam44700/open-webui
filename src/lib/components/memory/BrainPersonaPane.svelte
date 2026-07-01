<script lang="ts">
	// Onglet « Mon assistant » (feature 017) : édite SOUL.md (le caractère de l'assistant).
	// Sauvegarde EXPLICITE (pas d'autosave) : « Enregistrer » / « Annuler ». Réinitialiser =
	// confirmation + undo local. État « Enregistré » honnête (seulement après succès serveur).
	// UI premium : gabarits en cartes, éditeur en carte avec en-tête, skeleton, micro-interactions.
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { getPersona, savePersona, resetPersona } from '$lib/apis/memory';
	import { PERSONA_TEMPLATES } from './personaTemplates';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let loaded = false;
	let loadError = false;
	let content = '';
	let original = '';
	let saving = false;
	let justSaved = false;
	// Contenu d'avant la dernière réinitialisation, pour proposer « Annuler la réinitialisation ».
	let preReset: string | null = null;
	let confirmingReset = false;
	let activeTemplate: string | null = null;

	$: dirty = content !== original;

	const load = async () => {
		loaded = false;
		loadError = false;
		try {
			const data = await getPersona(localStorage.token);
			content = data.content ?? '';
			original = content;
		} catch (e) {
			loadError = true;
		} finally {
			loaded = true;
		}
	};

	onMount(load);

	const applyTemplate = (id: string, tplContent: string) => {
		content = tplContent;
		preReset = null;
		activeTemplate = id;
	};

	const save = async () => {
		saving = true;
		try {
			const data = await savePersona(localStorage.token, content);
			original = data.content ?? content;
			content = original;
			preReset = null;
			justSaved = true;
			setTimeout(() => (justSaved = false), 2400);
		} catch (e: any) {
			toast.error(e?.error?.message ?? $i18n.t("Impossible d'enregistrer."));
		} finally {
			saving = false;
		}
	};

	const cancel = () => {
		content = original;
		preReset = null;
		activeTemplate = null;
	};

	const doReset = async () => {
		try {
			const data = await resetPersona(localStorage.token);
			preReset = content;
			content = data.content ?? '';
		} catch (e) {
			toast.error($i18n.t('Impossible de réinitialiser.'));
		} finally {
			confirmingReset = false;
		}
	};

	const undoReset = () => {
		if (preReset !== null) {
			content = preReset;
			preReset = null;
		}
	};
</script>

<div class="w-full py-5">
	{#if !loaded}
		<!-- Skeleton (imite la mise en page finale) -->
		<div class="animate-pulse">
			<div class="h-3.5 w-40 rounded bg-gray-100 dark:bg-gray-800 mb-3"></div>
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mb-4">
				{#each Array(3) as _}
					<div class="h-[68px] rounded-xl bg-gray-100 dark:bg-gray-800"></div>
				{/each}
			</div>
			<div class="h-[55vh] min-h-[320px] rounded-2xl bg-gray-100 dark:bg-gray-800"></div>
		</div>
	{:else if loadError}
		<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-6 text-sm text-gray-600 dark:text-gray-300">
			{$i18n.t("Impossible de lire la personnalité de l'assistant pour le moment.")}
			<button class="ml-2 font-medium underline underline-offset-2" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else}
		<!-- Gabarits prêts à l'emploi (cartes) -->
		<div class="mb-4">
			<div class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
				{$i18n.t('Partir d’un modèle')}
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
				{#each PERSONA_TEMPLATES.filter((t) => t.id !== 'default') as tpl}
					<button
						class="group text-left rounded-xl border p-3.5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_2px_10px_rgba(0,0,0,0.05)] focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-300 dark:focus-visible:ring-gray-700 {activeTemplate ===
						tpl.id
							? 'border-gray-900 dark:border-white bg-gray-50 dark:bg-gray-850'
							: 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'}"
						on:click={() => applyTemplate(tpl.id, tpl.content)}
					>
						<div class="text-sm font-semibold text-gray-900 dark:text-white">{tpl.label}</div>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-snug">{tpl.description}</p>
					</button>
				{/each}
			</div>
		</div>

		<!-- Éditeur en carte (en-tête fin + zone d'écriture) -->
		<div
			class="rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden focus-within:border-gray-400 dark:focus-within:border-gray-600 focus-within:ring-4 focus-within:ring-gray-100 dark:focus-within:ring-gray-800/50 transition"
		>
			<div class="flex items-center justify-between px-4 h-11 border-b border-gray-100 dark:border-gray-800/70 bg-gray-50/60 dark:bg-gray-850/40">
				<span class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('Personnalité')}</span>
				<div class="text-xs h-4 flex items-center">
					{#if justSaved}
						<span class="inline-flex items-center gap-1 text-green-600 dark:text-green-500 font-medium">
							<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 9.7a1 1 0 1 1 1.4-1.4l3.3 3.29 6.8-6.8a1 1 0 0 1 1.4 0Z" clip-rule="evenodd"/></svg>
							{$i18n.t('Enregistré')}
						</span>
					{:else if preReset !== null}
						<button class="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white underline underline-offset-2" on:click={undoReset}>
							{$i18n.t('Annuler la réinitialisation')}
						</button>
					{:else if dirty}
						<span class="text-gray-400 dark:text-gray-500">{$i18n.t('Non enregistré')}</span>
					{/if}
				</div>
			</div>
			<textarea
				class="w-full h-[52vh] min-h-[320px] bg-transparent p-4 text-sm leading-relaxed resize-y outline-none border-0 focus:ring-0"
				bind:value={content}
				placeholder={$i18n.t(
					"Ex. : Tu es mon bras droit exécutif. Tu vas droit au but, en français. Tu n'inventes jamais."
				)}
				spellcheck="false"
			></textarea>
		</div>

		<!-- Barre d'actions -->
		<div class="flex items-center justify-end gap-2 mt-3">
			{#if confirmingReset}
				<span class="text-xs text-gray-500 dark:text-gray-400 mr-1">{$i18n.t('Repartir du modèle par défaut ?')}</span>
				<button class="px-3 py-2 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition" on:click={() => (confirmingReset = false)}>
					{$i18n.t('Non')}
				</button>
				<button class="px-3 py-2 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 transition" on:click={doReset}>
					{$i18n.t('Oui, réinitialiser')}
				</button>
			{:else}
				<button
					class="mr-auto px-3 py-2 rounded-lg text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => (confirmingReset = true)}
				>
					{$i18n.t('Réinitialiser')}
				</button>
				<button
					class="px-3 py-2 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-800 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
					disabled={!dirty || saving}
					on:click={cancel}
				>
					{$i18n.t('Annuler')}
				</button>
				<button
					class="px-4 py-2 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40 hover:opacity-90 transition"
					disabled={!dirty || saving}
					on:click={save}
				>
					{saving ? $i18n.t('Enregistrement…') : $i18n.t('Enregistrer')}
				</button>
			{/if}
		</div>
	{/if}
</div>
