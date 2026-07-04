<script lang="ts">
	// Rend la « mission » d'un agent en cartes lisibles (Identité / Mission / …).
	// Réutilisé par l'Atelier (agent généré) et l'aperçu des agents prêts à l'emploi.
	import { fly } from 'svelte/transition';

	import { parseSoulSections } from './soul';

	export let soul: string | null | undefined = '';
	// Animation d'entrée (jolie dans l'Atelier ; on peut la couper ailleurs).
	export let animate = true;

	$: sections = parseSoulSections(soul);
</script>

<div class="space-y-3">
	{#each sections as s, idx (s.title + idx)}
		<div
			class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"
			in:fly={{ y: animate ? 10 : 0, duration: animate ? 250 : 0, delay: animate ? 60 * idx : 0 }}
		>
			<div class="flex items-center gap-2 text-sm font-semibold">
				<span>{s.icon}</span>{s.title}
			</div>
			{#if s.body}
				<div class="text-sm text-gray-600 dark:text-gray-300 mt-2 whitespace-pre-line leading-relaxed">
					{s.body}
				</div>
			{/if}
		</div>
	{/each}
</div>
