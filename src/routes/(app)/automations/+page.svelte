<script lang="ts">
	// Porte unique (SPEC-automatisations-porte-unique) : les Automatisations vivent DANS
	// l'Espace de travail, pour garder l'en-tête et la barre d'onglets du hub (correction
	// demandée par Michael le 2026-07-20 — sans ça on sortait du hub et on perdait la
	// navigation vers Agents / Tâches / Bibliothèque).
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		goto('/workspace/automations', { replaceState: true });
	});
</script>
