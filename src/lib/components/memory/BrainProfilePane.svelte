<script lang="ts">
	// Onglet « Mon profil » (feature 017) : édite USER.md (qui est le dirigeant).
	// Sauvegarde EXPLICITE. Limite douce (message compréhensible, saisie jamais perdue).
	// UI premium : éditeur en carte avec en-tête (jauge douce + statut animé), skeleton.
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { getProfile, saveProfile } from '$lib/apis/memory';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let loaded = false;
	let loadError = false;
	let content = '';
	let original = '';
	let charLimit = 1375;
	let saving = false;
	let justSaved = false;

	$: dirty = content !== original;
	$: tooLong = content.length > charLimit;
	$: fillRatio = Math.min(1, content.length / charLimit);
	$: nearLimit = fillRatio > 0.85;

	const load = async () => {
		loaded = false;
		loadError = false;
		try {
			const data = await getProfile(localStorage.token);
			content = data.content ?? '';
			original = content;
			charLimit = data.char_limit ?? 1375;
		} catch (e) {
			loadError = true;
		} finally {
			loaded = true;
		}
	};

	onMount(load);

	const save = async () => {
		if (tooLong) return;
		saving = true;
		try {
			const data = await saveProfile(localStorage.token, content);
			original = data.content ?? content;
			content = original;
			justSaved = true;
			setTimeout(() => (justSaved = false), 2400);
		} catch (e: any) {
			toast.error(e?.error?.message ?? $i18n.t("Impossible d'enregistrer."));
		} finally {
			saving = false;
		}
	};

	const cancel = () => (content = original);
</script>

<div class="w-full py-5">
	{#if !loaded}
		<div class="animate-pulse">
			<div class="h-[52vh] min-h-[300px] rounded-2xl bg-gray-100 dark:bg-gray-800"></div>
		</div>
	{:else if loadError}
		<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-6 text-sm text-gray-600 dark:text-gray-300">
			{$i18n.t('Impossible de lire votre profil pour le moment.')}
			<button class="ml-2 font-medium underline underline-offset-2" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else}
		<!-- Éditeur en carte -->
		<div
			class="rounded-2xl border overflow-hidden transition {tooLong
				? 'border-amber-400/70 focus-within:ring-4 focus-within:ring-amber-100 dark:focus-within:ring-amber-900/30'
				: 'border-gray-200 dark:border-gray-800 focus-within:border-gray-400 dark:focus-within:border-gray-600 focus-within:ring-4 focus-within:ring-gray-100 dark:focus-within:ring-gray-800/50'}"
		>
			<div class="flex items-center justify-between px-4 h-11 border-b border-gray-100 dark:border-gray-800/70 bg-gray-50/60 dark:bg-gray-850/40">
				<span class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('Votre profil')}</span>
				<div class="flex items-center gap-3 text-xs h-4">
					{#if justSaved}
						<span class="inline-flex items-center gap-1 text-green-600 dark:text-green-500 font-medium">
							<svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 9.7a1 1 0 1 1 1.4-1.4l3.3 3.29 6.8-6.8a1 1 0 0 1 1.4 0Z" clip-rule="evenodd"/></svg>
							{$i18n.t('Enregistré')}
						</span>
					{:else if dirty}
						<span class="text-gray-400 dark:text-gray-500">{$i18n.t('Non enregistré')}</span>
					{/if}
					<!-- Jauge douce (pas de chiffre technique) : se colore seulement à l'approche de la limite -->
					<span class="inline-block w-16 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden" aria-hidden="true">
						<span
							class="block h-full rounded-full transition-all duration-300 {tooLong
								? 'bg-red-500'
								: nearLimit
									? 'bg-amber-500'
									: 'bg-gray-300 dark:bg-gray-600'}"
							style="width: {fillRatio * 100}%"
						></span>
					</span>
				</div>
			</div>
			<textarea
				class="w-full h-[50vh] min-h-[300px] bg-transparent p-4 text-sm leading-relaxed resize-y outline-none border-0 focus:ring-0"
				bind:value={content}
				placeholder={$i18n.t(
					'Ex. : Je dirige une PME de conseil de 12 personnes. Je préfère les réponses directes en français. Mes clients sont surtout des artisans.'
				)}
				spellcheck="false"
			></textarea>
		</div>

		<div class="flex items-center justify-end gap-2 mt-3">
			{#if tooLong}
				<span class="mr-auto text-xs text-amber-600 dark:text-amber-500">{$i18n.t("C'est un peu long, raccourcissez un peu pour l'enregistrer.")}</span>
			{/if}
			<button
				class="px-3 py-2 rounded-lg text-sm font-medium border border-gray-200 dark:border-gray-800 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
				disabled={!dirty || saving}
				on:click={cancel}
			>
				{$i18n.t('Annuler')}
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40 hover:opacity-90 transition"
				disabled={!dirty || saving || tooLong}
				on:click={save}
			>
				{saving ? $i18n.t('Enregistrement…') : $i18n.t('Enregistrer')}
			</button>
		</div>
	{/if}
</div>
