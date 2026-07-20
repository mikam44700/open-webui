<script lang="ts">
	// Porte unique (SPEC-automatisations-porte-unique) : les Automatisations vivent sur
	// /automations (page native + backend conservés). Cette route historique redirige
	// pour ne casser aucun lien — le « Bientôt disponible » n'a plus lieu d'être.
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		goto('/automations', { replaceState: true });
	});
</script>
