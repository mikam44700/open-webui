<script lang="ts">
	// Onglet « Mon profil » (feature 017) : édite USER.md (qui est le dirigeant).
	// Sauvegarde EXPLICITE. Limite douce (message compréhensible, saisie jamais perdue).
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { getProfile, saveProfile } from '$lib/apis/memory';
	import Spinner from '$lib/components/common/Spinner.svelte';

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
			setTimeout(() => (justSaved = false), 2000);
		} catch (e: any) {
			toast.error(e?.error?.message ?? $i18n.t("Impossible d'enregistrer."));
		} finally {
			saving = false;
		}
	};

	const cancel = () => (content = original);
</script>

<div class="max-w-3xl mx-auto py-4">
	{#if !loaded}
		<div class="flex justify-center py-16"><Spinner /></div>
	{:else if loadError}
		<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-6 text-sm text-gray-600 dark:text-gray-300">
			{$i18n.t('Impossible de lire votre profil pour le moment.')}
			<button class="ml-2 underline" on:click={load}>{$i18n.t('Réessayer')}</button>
		</div>
	{:else}
		<div class="mb-4">
			<h2 class="text-base font-semibold text-gray-900 dark:text-white">{$i18n.t('Qui vous êtes')}</h2>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				{$i18n.t(
					"Décrivez qui vous êtes pour que votre assistant vous connaisse et personnalise ses réponses, sans que vous ayez à le répéter."
				)}
			</p>
		</div>

		<textarea
			class="w-full h-56 rounded-2xl border {tooLong ? 'border-amber-400' : 'border-gray-200 dark:border-gray-800'} bg-transparent p-4 text-sm resize-y outline-none focus:border-gray-400 dark:focus:border-gray-600 transition"
			bind:value={content}
			placeholder={$i18n.t(
				'Ex. : Je dirige une PME de conseil de 12 personnes. Je préfère les réponses directes en français. Mes clients sont surtout des artisans.'
			)}
			spellcheck="false"
		></textarea>

		<div class="flex items-center justify-between mt-3">
			<div class="text-xs">
				{#if justSaved}
					<span class="text-green-600 dark:text-green-500 font-medium">{$i18n.t('Enregistré')}</span>
				{:else if tooLong}
					<span class="text-amber-600 dark:text-amber-500">{$i18n.t("C'est un peu long, raccourcissez un peu pour l'enregistrer.")}</span>
				{:else if dirty}
					<span class="text-gray-400">{$i18n.t('Modifications non enregistrées')}</span>
				{/if}
			</div>

			<div class="flex items-center gap-2">
				<button
					class="px-3 py-1.5 rounded-lg text-xs border border-gray-200 dark:border-gray-800 disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					disabled={!dirty || saving}
					on:click={cancel}
				>
					{$i18n.t('Annuler')}
				</button>
				<button
					class="px-4 py-1.5 rounded-lg text-xs bg-gray-900 dark:bg-white text-white dark:text-gray-900 disabled:opacity-40 transition"
					disabled={!dirty || saving || tooLong}
					on:click={save}
				>
					{saving ? $i18n.t('Enregistrement…') : $i18n.t('Enregistrer')}
				</button>
			</div>
		</div>
	{/if}
</div>
