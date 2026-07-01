<script lang="ts">
	// Onglet « Mon assistant » (feature 017) : édite SOUL.md (le caractère de l'assistant).
	// Sauvegarde EXPLICITE (pas d'autosave) : « Enregistrer » / « Annuler ». Réinitialiser =
	// confirmation + undo local. État « Enregistré » honnête (seulement après succès serveur).
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { getPersona, savePersona, resetPersona } from '$lib/apis/memory';
	import { PERSONA_TEMPLATES } from './personaTemplates';
	import Spinner from '$lib/components/common/Spinner.svelte';

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

	const applyTemplate = (tplContent: string) => {
		content = tplContent;
		preReset = null;
	};

	const save = async () => {
		saving = true;
		try {
			const data = await savePersona(localStorage.token, content);
			original = data.content ?? content;
			content = original;
			preReset = null;
			justSaved = true;
			setTimeout(() => (justSaved = false), 2000);
		} catch (e: any) {
			toast.error(e?.error?.message ?? $i18n.t("Impossible d'enregistrer."));
		} finally {
			saving = false;
		}
	};

	const cancel = () => {
		content = original;
		preReset = null;
	};

	const doReset = async () => {
		try {
			const data = await resetPersona(localStorage.token);
			preReset = content; // garde l'ancien pour un undo immédiat
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

<div class="max-w-3xl mx-auto py-4">
	{#if !loaded}
		<div class="flex justify-center py-16"><Spinner /></div>
	{:else if loadError}
		<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-6 text-sm text-gray-600 dark:text-gray-300">
			{$i18n.t("Impossible de lire la personnalité de l'assistant pour le moment.")}
			<button class="ml-2 underline" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else}
		<!-- Explication pédagogique -->
		<div class="mb-4">
			<h2 class="text-base font-semibold text-gray-900 dark:text-white">
				{$i18n.t("Le caractère de votre assistant")}
			</h2>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				{$i18n.t(
					"Décrivez comment vous voulez qu'il se comporte : son rôle, son ton, ses règles. Il en tiendra compte dans toutes vos conversations."
				)}
			</p>
		</div>

		<!-- Gabarits prêts à l'emploi -->
		<div class="mb-3">
			<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
				{$i18n.t('Partir d’un modèle')}
			</div>
			<div class="flex flex-wrap gap-2">
				{#each PERSONA_TEMPLATES.filter((t) => t.id !== 'default') as tpl}
					<button
						class="px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						title={tpl.description}
						on:click={() => applyTemplate(tpl.content)}
					>
						{tpl.label}
					</button>
				{/each}
			</div>
		</div>

		<textarea
			class="w-full h-72 rounded-2xl border border-gray-200 dark:border-gray-800 bg-transparent p-4 text-sm resize-y outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
			bind:value={content}
			placeholder={$i18n.t(
				"Ex. : Tu es mon bras droit exécutif. Tu vas droit au but, en français. Tu n'inventes jamais."
			)}
			spellcheck="false"
		></textarea>

		<!-- Barre d'actions -->
		<div class="flex items-center justify-between mt-3">
			<div class="text-xs">
				{#if justSaved}
					<span class="text-green-600 dark:text-green-500 font-medium">{$i18n.t('Enregistré')}</span>
				{:else if preReset !== null}
					<button class="text-gray-500 dark:text-gray-400 underline" on:click={undoReset}>
						{$i18n.t('Annuler la réinitialisation')}
					</button>
				{:else if dirty}
					<span class="text-gray-400">{$i18n.t('Modifications non enregistrées')}</span>
				{/if}
			</div>

			<div class="flex items-center gap-2">
				{#if confirmingReset}
					<span class="text-xs text-gray-500 dark:text-gray-400 mr-1">{$i18n.t('Repartir du modèle par défaut ?')}</span>
					<button class="px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-800" on:click={() => (confirmingReset = false)}>
						{$i18n.t('Non')}
					</button>
					<button class="px-3 py-1.5 rounded-lg text-xs bg-gray-900 dark:bg-white text-white dark:text-gray-900" on:click={doReset}>
						{$i18n.t('Oui, réinitialiser')}
					</button>
				{:else}
					<button
						class="px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						on:click={() => (confirmingReset = true)}
					>
						{$i18n.t('Réinitialiser')}
					</button>
					<button
						class="px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-800 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
						disabled={!dirty || saving}
						on:click={cancel}
					>
						{$i18n.t('Annuler')}
					</button>
					<button
						class="px-4 py-1.5 rounded-lg text-xs bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40 transition"
						disabled={!dirty || saving}
						on:click={save}
					>
						{saving ? $i18n.t('Enregistrement…') : $i18n.t('Enregistrer')}
					</button>
				{/if}
			</div>
		</div>
	{/if}
</div>
