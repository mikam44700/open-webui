<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	import ActiveBadge from '$lib/components/common/ActiveBadge.svelte';
	import type { DisplayState } from '$lib/engine/health';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let state: DisplayState = 'unknown';
	/** Libellé du cas nominal : « Actif » par défaut, « Connecté » pour une plateforme. */
	export let activeLabel = 'Active';
	/** Affiche un libellé discret quand ce n'est pas actif, au lieu de ne rien montrer. */
	export let showIdle = false;
	/** Libellé du cas en panne : « Hors service » par défaut, « Non connecté » pour une plateforme. */
	export let downLabel = 'Out of service';

	const dotClass: Record<DisplayState, string> = {
		ok: 'bg-green-500',
		warning: 'bg-amber-500',
		down: 'bg-red-500',
		unknown: 'bg-gray-400 dark:bg-gray-600'
	};

	const textClass: Record<DisplayState, string> = {
		ok: 'text-green-600 dark:text-green-400',
		warning: 'text-amber-600 dark:text-amber-400',
		down: 'text-red-600 dark:text-red-400',
		unknown: 'text-gray-500'
	};

	// Rien à signaler ne mérite pas un tag. On n'affiche que ce qui demande une action,
	// et « je ne sais pas » reste silencieux plutôt que de ressembler à une panne.
	$: labelKey = {
		ok: '',
		warning: 'Needs attention',
		down: downLabel,
		unknown: 'Not reported'
	} as Record<DisplayState, string>;
</script>

{#if state === 'ok'}
	<ActiveBadge label={activeLabel} />
{:else if state !== 'unknown' || showIdle}
	<span class="flex shrink-0 items-center gap-1.5">
		<span class="inline-block size-2 shrink-0 rounded-full {dotClass[state]}"></span>
		<span class="shrink-0 text-[10px] font-medium {textClass[state]}">
			{$i18n.t(labelKey[state])}
		</span>
	</span>
{/if}
