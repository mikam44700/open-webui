<script lang="ts">
	// Indicateur « Actif » unifié : point vert clignotant + libellé. Affiché quand un composant
	// est réellement opérationnel. Remplace les tags négatifs redondants (« Indisponible »,
	// « Non connecté ») : on met en avant ce qui marche, on ne surcharge pas l'écran du reste.
	// L'animation se coupe si l'utilisateur a désactivé les animations de son système.
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18nType } from 'i18next';

	const i18n = getContext<Writable<I18nType>>('i18n');

	export let label = 'Active';
</script>

<span
	class="inline-flex items-center gap-1 whitespace-nowrap text-[10px] font-medium text-green-600 dark:text-green-400"
>
	<span class="relative flex size-2 shrink-0">
		<span
			class="absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-60 motion-safe:animate-ping"
		></span>
		<span class="relative inline-flex size-2 rounded-full bg-green-500"></span>
	</span>
	{$i18n.t(label)}
</span>
