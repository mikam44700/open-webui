<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import { createPresentation } from '$lib/apis/google-services';

	const i18n = getContext('i18n');

	// Google connecté ? (dérivé du dashboard) — état honnête, pas de bouton mort.
	export let googleConnected: boolean | 'unknown' = 'unknown';

	let title = '';
	let outline = '';
	let creating = false;

	const submit = async () => {
		if (!title.trim()) {
			toast.error($i18n.t('Donnez un titre à la présentation.'));
			return;
		}
		creating = true;
		try {
			const slides = outline
				.split('\n')
				.map((l) => l.trim())
				.filter(Boolean);
			const res = await createPresentation(localStorage.token, title.trim(), slides);
			const url = res?.presentation?.url;
			toast.success($i18n.t('Présentation créée'));
			title = '';
			outline = '';
			if (url) window.open(url, '_blank');
		} catch (err: any) {
			if (err?.error?.code === 'google_not_connected') {
				toast.error($i18n.t('Connectez Google dans Intégrations.'));
			} else {
				toast.error(typeof err === 'string' ? err : $i18n.t('Création impossible'));
			}
		} finally {
			creating = false;
		}
	};
</script>

<div class="flex flex-col gap-2.5 p-4 rounded-2xl border border-gray-100 dark:border-gray-850">
	<div class="flex items-center justify-between">
		<div class="text-sm font-medium">{$i18n.t('Présentation Google Slides')}</div>
		{#if googleConnected === false}
			<span class="text-[11px] px-2 py-0.5 rounded-full text-gray-600 bg-gray-500/10 dark:text-gray-400">
				{$i18n.t('Google non connecté')}
			</span>
		{/if}
	</div>

	<input
		class="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 outline-none text-sm"
		bind:value={title}
		placeholder={$i18n.t('Titre de la présentation')}
	/>
	<textarea
		class="w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-850 outline-none text-sm resize-none"
		rows="3"
		bind:value={outline}
		placeholder={$i18n.t('Plan (optionnel) : une diapo par ligne')}
	></textarea>

	<button
		class="self-end px-3 py-1.5 rounded-lg text-sm bg-black text-white dark:bg-white dark:text-black disabled:opacity-50 transition"
		disabled={creating}
		on:click={submit}
	>
		{#if creating}
			<Spinner className="size-3.5" />
		{:else}
			{$i18n.t('Créer la présentation')}
		{/if}
	</button>
</div>
