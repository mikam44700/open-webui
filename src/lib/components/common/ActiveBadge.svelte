<script lang="ts">
	// Indicateur « Actif » unifié : point vert clignotant (même style que « État du moteur »)
	// + libellé. Affiché quand un fournisseur / canal / connecteur est réellement actif ou
	// connecté. Remplace les tags négatifs redondants (« Désactivé », « Non connecté »).
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	export let label = 'Actif';
</script>

<span
	class="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400 whitespace-nowrap"
>
	<span class="relative flex size-2 shrink-0">
		<span
			class="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60 animate-ping"
		></span>
		<span class="relative inline-flex size-2 rounded-full bg-emerald-500"></span>
	</span>
	{$i18n.t(label)}
</span>
