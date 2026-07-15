<script lang="ts">
	// Onglet « Mon assistant » (feature 017) : édite SOUL.md — le caractère de l'agent qui sert le
	// chat, c'est-à-dire le profil « default » du moteur (= Mike, l'orchestrateur). Les six autres
	// agents du socle ont leur propre SOUL dans `profiles/<agent>/` : cette page ne les touche PAS.
	// Mike est incarné dans la bannière de l'onglet (cf. `+layout.svelte`), comme Adam pour le coffre.
	//
	// Sauvegarde EXPLICITE (pas d'autosave) : « Enregistrer » / « Annuler ». Réinitialiser =
	// confirmation + undo local. État « Enregistré » honnête (seulement après succès serveur).
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { getPersona, savePersona } from '$lib/apis/memory';
	import { applyTone, resetToFactory } from '$lib/memory/personaSections';
	import { AGENT_TEMPLATES } from '$lib/components/agents/templates';
	import { PERSONA_TONES } from './personaTemplates';

	// Version d'usine de l'orchestrateur (profil « default »), pour le bouton « Réinitialiser ».
	const FACTORY_SOUL = AGENT_TEMPLATES.find((t) => t.id === 'mike-chef-orchestre')?.soul ?? '';

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
	$: charCount = content.length;

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

	// Un ton ne remplace QUE sa section : l'identité, la méthode et l'équipe de l'agent survivent.
	const applyToneTemplate = (id: string, body: string) => {
		content = applyTone(content, body);
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

	// Réinitialiser = revenir à la version d'usine de l'agent, en GARDANT son équipe réelle.
	// Local et non enregistré (comme le reste de la page) : le dirigeant voit avant de valider.
	// On n'appelle plus `resetPersona` : le défaut du serveur est un assistant générique, sans
	// équipe ni marqueurs — il effaçait l'orchestrateur au lieu de le restaurer.
	const doReset = () => {
		preReset = content;
		content = resetToFactory(content, FACTORY_SOUL);
		activeTemplate = null;
		confirmingReset = false;
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
		<!-- Skeleton (imite la mise en page finale : gabarits, éditeur) -->
		<div class="animate-pulse">
			<div class="h-3.5 w-40 rounded bg-gray-100 dark:bg-gray-800 mb-3"></div>
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
				{#each Array(3) as _}
					<div class="h-[84px] rounded-2xl bg-gray-100 dark:bg-gray-800"></div>
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
		<!-- Tons prêts à l'emploi (cartes premium) : ils n'ajustent QUE la façon de parler. -->
		<div class="mb-5">
			<div class="flex flex-wrap items-baseline gap-x-2 mb-2.5">
				<span class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
					{$i18n.t('Sa façon de vous parler')}
				</span>
				<span class="text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t('— ajuste le ton, le reste ne bouge pas')}
				</span>
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
				{#each PERSONA_TONES as tone}
					<button
						class="group relative overflow-hidden text-left rounded-2xl border p-4 card-lift bg-white dark:bg-gray-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-300 dark:focus-visible:ring-gray-700 {activeTemplate ===
						tone.id
							? 'border-gray-900 dark:border-white ring-1 ring-inset ring-gray-900 dark:ring-white'
							: 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'}"
						on:click={() => applyToneTemplate(tone.id, tone.body)}
					>
						<div class="flex items-center justify-between gap-2">
							<div class="text-sm font-semibold text-gray-900 dark:text-white">{tone.label}</div>
							{#if activeTemplate === tone.id}
								<svg class="w-4 h-4 shrink-0 text-gray-900 dark:text-white" viewBox="0 0 20 20" fill="currentColor">
									<path fill-rule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 9.7a1 1 0 1 1 1.4-1.4l3.3 3.29 6.8-6.8a1 1 0 0 1 1.4 0Z" clip-rule="evenodd" />
								</svg>
							{/if}
						</div>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5 leading-snug">{tone.description}</p>
					</button>
				{/each}
			</div>
		</div>

		<!-- Éditeur en carte (en-tête fin + zone d'écriture + pied discret) -->
		<div
			class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden focus-within:border-gray-400 dark:focus-within:border-gray-600 focus-within:ring-4 focus-within:ring-gray-100 dark:focus-within:ring-gray-800/50 transition"
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
						<span class="inline-flex items-center gap-1.5 text-gray-400 dark:text-gray-500">
							<span class="h-1.5 w-1.5 rounded-full bg-amber-500"></span>
							{$i18n.t('Non enregistré')}
						</span>
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
			<div class="flex items-center justify-end px-4 h-8 border-t border-gray-100 dark:border-gray-800/70 bg-gray-50/60 dark:bg-gray-850/40">
				<span class="text-[11px] tabular-nums text-gray-400 dark:text-gray-500">
					{charCount.toLocaleString('fr-FR')}
					{$i18n.t('caractères')}
				</span>
			</div>
		</div>

		<!-- Barre d'actions -->
		<div class="flex items-center justify-end gap-2 mt-3">
			{#if confirmingReset}
				<span class="text-xs text-gray-500 dark:text-gray-400 mr-1">{$i18n.t('Repartir de sa version d’origine ? Son équipe est conservée.')}</span>
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
					class="btn-premium px-4 py-2 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40"
					disabled={!dirty || saving}
					on:click={save}
				>
					{saving ? $i18n.t('Enregistrement…') : $i18n.t('Enregistrer')}
				</button>
			{/if}
		</div>
	{/if}
</div>
