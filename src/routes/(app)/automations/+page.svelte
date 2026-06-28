<script>
	// Page Automatisations déplacée dans le hub « Espace de travail » (onglet Automatisations).
	// On redirige l'ancienne route pour ne casser aucun lien/favori existant.
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		goto('/workspace/automations');
	});
</script>
