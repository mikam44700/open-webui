<script lang="ts">
	/**
	 * Valeur a recopier ailleurs — code d'autorisation, commande de terminal.
	 *
	 * Recopier un code a la main est le moment ou l'on se trompe : caracteres
	 * ambigus, code qui expire pendant qu'on le relit. D'ou le bouton, et une
	 * taille de texte lisible d'un coup d'oeil.
	 */
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let value = '';
	export let label = '';
	/** `code` grossit le texte et l'espace les lettres ; `command` reste compact. */
	export let variant: 'code' | 'command' = 'code';

	let copie = false;
	let minuterie: ReturnType<typeof setTimeout> | null = null;

	const copier = async () => {
		try {
			await navigator.clipboard.writeText(value);
		} catch {
			// Presse-papiers refuse (page non securisee, permission) : on selectionne
			// le texte pour que la copie manuelle reste possible.
			const champ = document.getElementById(`copie-${label}-${value}`);
			if (champ) {
				const plage = document.createRange();
				plage.selectNodeContents(champ);
				const selection = window.getSelection();
				selection?.removeAllRanges();
				selection?.addRange(plage);
			}
			return;
		}
		copie = true;
		if (minuterie) clearTimeout(minuterie);
		minuterie = setTimeout(() => (copie = false), 2000);
	};
</script>

<div class="flex flex-col gap-1">
	{#if label}
		<span class="text-xs text-gray-500 dark:text-gray-400">{label}</span>
	{/if}

	<div
		class="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-900"
	>
		<code
			id="copie-{label}-{value}"
			class="min-w-0 flex-1 select-all break-all font-mono text-gray-900 dark:text-gray-100 {variant ===
			'code'
				? 'text-xl font-semibold tracking-[0.12em]'
				: 'text-[11px] leading-relaxed'}"
		>
			{value}
		</code>

		<button
			type="button"
			class="shrink-0 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-white dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-850"
			on:click={copier}
		>
			{copie ? $i18n.t('Copié') : $i18n.t('Copier')}
		</button>
	</div>
</div>
